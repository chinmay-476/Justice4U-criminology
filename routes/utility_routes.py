from flask import render_template, send_from_directory



def register_utility_routes(app):
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/manifest.json')
    def manifest():
        return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

    @app.route('/service-worker.js')
    def service_worker():
        return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

    @app.route('/sw.js')
    def sw_js():
        return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

    @app.route('/pwa-test')
    def pwa_test():
        return render_template('pwa_test.html')
