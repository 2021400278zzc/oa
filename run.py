import os

from app import create_app

port = os.getenv("PORT")

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)
