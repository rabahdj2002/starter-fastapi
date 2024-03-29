from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn, datetime, os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from random import randint
from appwrite.client import Client
from appwrite.services.databases import Databases

app = FastAPI()

client = Client()

(client
.set_endpoint('https://cloud.appwrite.io/v1')  # Your API Endpoint
.set_project('658abe9cee37aca3883a')  # Your project ID
.set_key(
    '6e3c936a3cf826b270fa6936879e3a65e4a5d3b7df7a80ee668fd6e7507c90fa1d98689d7188988b3fcefa164aac29d284dcd6b2ebdb9bdedeeed4730b1f1f87f1096967e7f4c656dbba3a1b2c68ef9640ea7242fcde6faff9aaab90104ff113f2dfbc1d9a756243a2d0b92f613cdd301b429a32cc24082b6258c988e8f66a4d')
)
databases = Databases(client)


def save(expire, otp, email):
    data = {
        "created_at": str(datetime.datetime.now()),
        "validity": expire,
        "email": email,
    }
    result = databases.create_document('6602ada00e1301e38f96', '6602b60648ad019bbdb4', f"doc_{otp}_dz", data)
    print(result)
    return result


def verify(otp, email):
    try:
        result = databases.get_document('6602ada00e1301e38f96', '6602b60648ad019bbdb4', f"doc_{otp}_dz")
    except:
        return 0 # error
    fmt = '%Y-%m-%d %H:%M:%S.%f'
    d1 = datetime.datetime.strptime(str(datetime.datetime.now())[:-4], fmt)
    d2 = datetime.datetime.strptime(str(result['created_at'])[:-7].replace('T', " "), fmt)
    delta = round((d1 - d2).total_seconds() / 60.0)
    print(delta)
    if delta > result["validity"]:
        return 1 # validity expired
    if result['email'] != email:
        raise 2 # wrong email
    if result['verified']:
        return 3 # already verified
    data = {
        "verified": True
    }
    databases.update_document('6602ada00e1301e38f96', '6602b60648ad019bbdb4', f"doc_{otp}_dz", data)
    return 4 # all good


class SendingRequest(BaseModel):
    company_name: str
    recipient_email: str
    expire: int | None = 30
    OTP: int | None = 000000


class VerificationRequest(BaseModel):
    recipient_email: str
    OTP: int


def send_email(company_name, recipient_email, subject, username, password, expire=30, OTP=None):
    expire = expire if expire != 0 else 30
    msg = MIMEMultipart()
    msg['From'] = f'{company_name} <{username}>'
    msg['To'] = recipient_email
    msg['Subject'] = subject
    message_body = f"""<!DOCTYPE html>
                        <html lang="en">
                          <head>
                            <meta charset="UTF-8" />
                            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                            <meta http-equiv="X-UA-Compatible" content="ie=edge" />
                            <title>Static Template</title>

                            <link
                              href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap"
                              rel="stylesheet"
                            />
                          </head>
                          <body
                            style="
                              margin: 0;
                              font-family: 'Poppins', sans-serif;
                              background: #ffffff;
                              font-size: 14px;
                            "
                          >
                              <main>
                                <div
                                  style="
                                    margin: 0;
                                    margin-top: 70px;
                                    padding: 92px 30px 115px;
                                    background: #ffffff;
                                    border-radius: 30px;
                                    text-align: center;
                                  "
                                >
                                  <div style="width: 100%; max-width: 489px; margin: 0 auto;">
                                    <h1
                                      style="
                                        margin: 0;
                                        font-size: 24px;
                                        font-weight: 500;
                                        color: #1f1f1f;
                                      "
                                    >
                                      Your One Time Password
                                    </h1>
                                    <p
                                      style="
                                        margin: 0;
                                        margin-top: 17px;
                                        font-size: 16px;
                                        font-weight: 500;
                                      "
                                    >
                                      Dear User,
                                    </p>
                                    <p
                                      style="
                                        margin: 0;
                                        margin-top: 17px;
                                        font-weight: 500;
                                        letter-spacing: 0.56px;
                                      "
                                    >
                                      Thank you for choosing {company_name}. Use the following OTP
                                      to complete the procedure. OTP is valid for
                                      <span style="font-weight: 600; color: #1f1f1f;">{expire} minutes</span>.
                                      Do not share this code with others, including {company_name} employees.
                                    </p>
                                    <p
                                      style="
                                        margin: 0;
                                        margin-top: 60px;
                                        font-size: 40px;
                                        font-weight: 600;
                                        letter-spacing: 25px;
                                        color: #ba3d4f;
                                      "
                                    >
                                      {OTP}
                                    </p>
                                  </div>
                                </div>
                              </main>
                          </body>
                        </html>
                        """

    msg.attach(MIMEText(message_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(username, password)
            server.sendmail(username, recipient_email, msg.as_string())
        save(expire, OTP, recipient_email)
        return "Email sent successfully!"
    except Exception as e:
        return "Failed to send email:" + str(e)


@app.post("/send_otp")
async def send_otp(request: SendingRequest):
    company_name = request.company_name
    recipient_email = request.recipient_email
    expire = request.expire
    OTP = request.OTP if request.OTP != 0 else randint(100000, 999999)
    subject = f"Your {company_name} OTP."
    gmail_username = os.getenv('username')
    gmail_password = os.getenv('pass')

    send_email(company_name, recipient_email, subject, gmail_username, gmail_password, expire, OTP)

    return {"status": "Success",
            "message": "OTP was successfully sent",
            "otp": OTP,
            "validity": f"{expire} min"}


@app.post("/verify_otp")
async def verify_otp(request: VerificationRequest):
    recipient_email = request.recipient_email
    OTP = request.OTP

    status = verify(OTP, recipient_email)
    match status:
        case 0:
            raise HTTPException(status_code=400, detail="Wrong OTP provided!")
        case 1:
            raise HTTPException(status_code=410, detail="OTP has expired!")
        case 2:
            raise HTTPException(status_code=400, detail="Wrong email address!")
        case 3:
            raise HTTPException(status_code=400, detail="OTP already verified!")
        case 4:
            return {"status": "success", "message": "OTP successfully verified"}


"""if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
"""
