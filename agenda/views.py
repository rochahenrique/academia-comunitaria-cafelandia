from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AgendamentoForm, CadastroForm
from .models import Agendamento


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