from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AgendamentoForm, CadastroForm, RelatorioForm
from .models import Agendamento, Comunicado, Horario


def _grupo_do_usuario(usuario):
    return usuario.grupos.first()


def _enviar_email(usuario, agendamento, acao):
    """Envia a confirmação (RF03/RF07). Sem e-mail cadastrado, não envia."""
    if not usuario.email:
        return
    corpo = (
        f"Olá, {usuario.username}!\n\n"
        f"Seu agendamento foi {acao}.\n"
        f"Grupo: {agendamento.grupo}\n"
        f"Data: {agendamento.data:%d/%m/%Y}\n"
        f"Horário: {agendamento.horario}\n"
    )
    send_mail(f"Agendamento {acao} - Academia Comunitária", corpo, None, [usuario.email])


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("agenda:home")
    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect("agenda:home")
    else:
        form = CadastroForm()
    return render(request, "agenda/cadastro.html", {"form": form})


@login_required
def home(request):
    grupo = _grupo_do_usuario(request.user)
    proximos = []
    if grupo:
        proximos = grupo.agendamentos.filter(
            status="confirmado", data__gte=timezone.localdate()
        ).select_related("horario")
    return render(request, "agenda/home.html", {"grupo": grupo, "proximos": proximos})


@login_required
def agendar(request):
    grupo = _grupo_do_usuario(request.user)
    if grupo is None:
        messages.error(
            request,
            "Seu usuário não está vinculado a um grupo. "
            "Peça ao administrador para cadastrar seu grupo.",
        )
        return redirect("agenda:home")

    if request.method == "POST":
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    agendamento = Agendamento.objects.create(
                        grupo=grupo,
                        horario=form.cleaned_data["horario"],
                        data=form.cleaned_data["data"],
                    )
            except IntegrityError:
                # Duas pessoas reservando ao mesmo tempo: o banco barra a segunda.
                form.add_error(
                    None, "Este horário acabou de ser reservado. Escolha outro."
                )
            else:
                _enviar_email(request.user, agendamento, "confirmado")
                messages.success(request, "Agendamento confirmado!")
                return redirect("agenda:home")
    else:
        form = AgendamentoForm()
    return render(request, "agenda/agendar.html", {"form": form})


@login_required
@require_POST
def cancelar(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk, grupo__responsavel=request.user)
    if agendamento.status == "confirmado":
        agendamento.status = "cancelado"
        agendamento.save(update_fields=["status"])
        _enviar_email(request.user, agendamento, "cancelado")
        messages.success(request, "Agendamento cancelado.")
    return redirect("agenda:home")

def comunicados(request):
    """Lista pública de comunicados e regras de uso (RF04)."""
    return render(
        request, "agenda/comunicados.html", {"comunicados": Comunicado.objects.all()}
    )


def _ocorrencias(inicio, fim, dia_semana):
    """Quantas vezes um dia da semana aparece entre duas datas."""
    total_dias = (fim - inicio).days + 1
    return sum(
        1
        for i in range(total_dias)
        if (inicio + timedelta(days=i)).weekday() == dia_semana
    )


@user_passes_test(lambda u: u.is_staff, login_url="login")
def relatorio(request):
    """Relatório de utilização, restrito ao administrador (RF06)."""
    form = RelatorioForm(request.GET or None)
    resultado = None

    if form.is_valid():
        inicio = form.cleaned_data["data_inicio"]
        fim = form.cleaned_data["data_fim"]
        base = Agendamento.objects.filter(data__range=(inicio, fim))
        confirmados = base.filter(status="confirmado")

        horarios = Horario.objects.filter(ativo=True).annotate(
            total=Count(
                "agendamentos",
                filter=Q(
                    agendamentos__status="confirmado",
                    agendamentos__data__range=(inicio, fim),
                ),
            )
        )
        linhas = []
        vagas_totais = 0
        for h in horarios:
            vagas = _ocorrencias(inicio, fim, h.dia_semana)
            vagas_totais += vagas
            linhas.append(
                {
                    "horario": h,
                    "total": h.total,
                    "vagas": vagas,
                    "ocupacao": round(100 * h.total / vagas) if vagas else 0,
                }
            )

        total_confirmados = confirmados.count()
        resultado = {
            "inicio": inicio,
            "fim": fim,
            "confirmados": total_confirmados,
            "cancelados": base.filter(status="cancelado").count(),
            "ocupacao_geral": (
                round(100 * total_confirmados / vagas_totais) if vagas_totais else 0
            ),
            "por_horario": linhas,
            "por_grupo": confirmados.values("grupo__nome")
            .annotate(total=Count("id"))
            .order_by("-total"),
        }

    return render(
        request, "agenda/relatorio.html", {"form": form, "resultado": resultado}
    )