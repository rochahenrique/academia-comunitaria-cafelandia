from django.contrib import admin

from .models import Agendamento, Comunicado, Grupo, Horario


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