from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Agendamento, Grupo, Horario

User = get_user_model()


class CadastroForm(UserCreationForm):
    """Cria o usuário e o grupo dele em um único cadastro (RF01)."""

    email = forms.EmailField(label="E-mail")
    nome_grupo = forms.CharField(label="Nome do grupo ou instituição", max_length=120)
    tipo_grupo = forms.ChoiceField(label="Tipo de grupo", choices=Grupo.TIPOS)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save()
        Grupo.objects.create(
            nome=self.cleaned_data["nome_grupo"],
            tipo=self.cleaned_data["tipo_grupo"],
            responsavel=user,
        )
        return user


class AgendamentoForm(forms.Form):
    """Valida as regras de negócio antes de criar a reserva (RF02)."""

    horario = forms.ModelChoiceField(
        queryset=Horario.objects.filter(ativo=True), label="Horário"
    )
    data = forms.DateField(
        label="Data", widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean_data(self):
        data = self.cleaned_data["data"]
        if data < timezone.localdate():
            raise ValidationError("Não é possível agendar em uma data passada.")
        return data

    def clean(self):
        dados = super().clean()
        horario = dados.get("horario")
        data = dados.get("data")
        if horario and data:
            if data.weekday() != horario.dia_semana:
                raise ValidationError(
                    "A data escolhida não cai no dia da semana deste horário."
                )
            if Agendamento.objects.filter(
                horario=horario, data=data, status="confirmado"
            ).exists():
                raise ValidationError("Este horário já está reservado nesta data.")
        return dados