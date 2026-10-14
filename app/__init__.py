import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from app import config
from app.sockets import register_socket_handlers

socketio = SocketIO()

def create_app():
    """Application factory for PC Controller."""
    template_dir = os.path.join(config.BASE_DIR, 'templates')
    static_dir = os.path.join(config.BASE_DIR, 'static')
    
    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )
    
    # Configure security and uploads
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_SIZE
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.system import system_bp
    from app.routes.control import control_bp
    from app.routes.files import files_bp
    from app.routes.pranks import pranks_bp
    from app.routes.stream import stream_bp
    from app.routes.apps import apps_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(pranks_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(apps_bp)
    
    # Main dashboard route
    @app.route('/')
    def index():
        return render_template('index.html', version=config.APP_VERSION)
        
    # Initialize WebSockets
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    register_socket_handlers(socketio)
    
    return app
