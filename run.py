import os
from app import create_app
from config import Config, DevConfig

_configs = {'dev': DevConfig, 'production': Config}
app = create_app(_configs.get(os.environ.get('FLASK_CONFIG', 'production'), Config))

if __name__ == '__main__':
    app.run(ssl_context='adhoc', debug=False)
