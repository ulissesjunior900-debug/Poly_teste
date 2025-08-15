from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, Email, Length, ValidationError
from models import Usuario


class UsuarioForm(FlaskForm):
    username = StringField('Username', validators=[Optional(), Length(min=3, max=80)])
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    funcao = StringField('Função', validators=[Optional(), Length(max=50)])
    senha = PasswordField('Senha', validators=[Optional(), Length(min=6, max=128)])
    ativo = BooleanField('Usuário Ativo')
    avatar = SelectField('Avatar', choices=[
        ('avatar1.png', 'Avatar 1'),
        ('avatar2.png', 'Avatar 2'),
        ('avatar3.png', 'Avatar 3'),
        ('avatar4.png', 'Avatar 4'),
        ('avatar5.png', 'Avatar 5')
    ], validators=[Optional()])
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(UsuarioForm, self).__init__(*args, **kwargs)
        self.obj_id = kwargs.get('obj_id', None)  # Adiciona suporte a obj_id

    def validate_email(self, email):
        usuario = Usuario.query.filter_by(email=email.data).first()
        if usuario and (not hasattr(self, 'obj_id') or usuario.id != self.obj_id):
            raise ValidationError('Este email já está em uso por outro usuário.')

    def validate_username(self, username):
        if username.data:  # Só valida se username foi fornecido (já que é Optional)
            usuario = Usuario.query.filter_by(username=username.data).first()
            if usuario and (not hasattr(self, 'obj_id') or usuario.id != self.obj_id):
                raise ValidationError('Este username já está em uso.')