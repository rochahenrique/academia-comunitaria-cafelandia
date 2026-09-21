from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage

from .models import Agendamento, Comunicado, Grupo, Horario

User = get_user_model()


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "responsavel")
    list_filter = ("tipo",)
    search_fields = ("nome",)


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ("dia_semana", "hora_inicio", "hora_fim", "ativo")
    list_filter = ("dia_semana", "ativo")


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("grupo", "data", "horario", "status")
    list_filter = ("status", "data")


@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "criado_em")
    list_filter = ("tipo",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.autor = request.user
        super().save_model(request, obj, form, change)

        # Aviso de manutenção por e-mail (RF07)
        if not change and obj.tipo == "manutencao":
            destinatarios = list(
                User.objects.filter(is_active=True)
                .exclude(email="")
                .values_list("email", flat=True)
            )
            if destinatarios:
                EmailMessage(
                    subject=f"Aviso: {obj.titulo}",
                    body=obj.mensagem,
                    bcc=destinatarios,
                ).send()