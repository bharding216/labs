from project import create_app

app = create_app()

if __name__ == '__main__':
    #app.run(host='localhost', port=2000, debug=True)
    app.run()