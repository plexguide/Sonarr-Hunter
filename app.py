# Assuming you're using Flask, but concept applies to other frameworks

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/logs')
def logs():
    return render_template('logs.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/user')
def user():
    return render_template('user.html')
