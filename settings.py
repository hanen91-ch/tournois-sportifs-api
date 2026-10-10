from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plateforme_tournois.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SWAGGER'] = {
    'title': 'Service Plateforme Tournois Sportifs',
    'version': '1.0.0',
    'securityDefinitions': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Écrire : Bearer <votre_token>'
        }
    }
}

db = SQLAlchemy(app)