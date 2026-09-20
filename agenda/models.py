from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Grupo(models.Model):
    """Organização da comunidade que usa a academia."""

    TIPOS = [
        ("escola", "Escola"),
        ("creche", "Creche"),
        ("orfanato", "Orfanato"),
        ("asilo", "Asilo"),
        ("ong", "ONG"),
        ("esportivo", "Grupo esportivo"),
        ("outro", "Outro"),
    ]

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="outro")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Horario(models.Model):
    """Faixa de horário fixa da semana (ex.: terça, 08:00 às 09:00)."""

    DIAS = [
        (0, "Segunda-feira"),
        (1, "Terça-feira"),
        (2, "Quarta-feira"),
        (3, "Quinta-feira"),
        (4, "Sexta-feira"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    dia_semana = models.IntegerField(choices=DIAS)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["dia_semana", "hora_inicio"]

    def clean(self):
        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            raise ValidationError("A hora final deve ser maior que a hora inicial.")

    def __str__(self):
        return (
            f"{self.get_dia_semana_display()} "
            f"{self.hora_inicio:%H:%M}-{self.hora_fim:%H:%M}"
        )


class Agendamento(models.Model):
    """Reserva de uma faixa de horário, por um grupo, em uma data."""

    STATUS = [
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
    ]

    grupo = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="agendamentos"
    )
    horario = models.ForeignKey(
        Horario, on_delete=models.PROTECT, related_name="agendamentos"
    )
    data = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default="confirmado")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data", "horario__hora_inicio"]
        constraints = [
            # Só pode existir UM agendamento confirmado por horário e data.
            # É a regra que evita conflitos (Objetivo 1 da validação).
            models.UniqueConstraint(
                fields=["horario", "data"],
                condition=Q(status="confirmado"),
                name="unico_agendamento_confirmado_por_horario_data",
            )
        ]

    def clean(self):
        if self.horario_id and self.data:
            if self.data.weekday() != self.horario.dia_semana:
                raise ValidationError(
                    "A data escolhida não cai no dia da semana deste horário."
                )

    def __str__(self):
        return f"{self.grupo} - {self.data:%d/%m/%Y} ({self.horario})"


class Comunicado(models.Model):
    """Aviso publicado pelo administrador (regras, manutenção, novidades)."""

    TIPOS = [
        ("aviso", "Aviso"),
        ("regra", "Regra de uso"),
        ("manutencao", "Manutenção programada"),
    ]

    titulo = models.CharField(max_length=150)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=12, choices=TIPOS, default="aviso")
    criado_em = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo