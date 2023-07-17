import uvicorn, random, string, traceback
from datetime import datetime
from models import User, UserUpdate, Email, EmailReply
from settings import PORT, HOST, client
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

current_time = datetime.now()


@app.get("/")
def get_server_status():
    return f'Server is started and running successfully in port: {PORT}'


#######################################################################################################################
####################################         Users Service        #####################################################
#######################################################################################################################
@app.get("/user/{email_id}")
async def get_user(email_id: str):
    mongo_filter = {
        "email_id": email_id
    }
    project = {
        "_id": 0
    }
    return client.privatemail.users.find_one(mongo_filter, project)


@app.post("/user/login")
def login_user(email: str, password: str):
    try:
        mongo_filter = {
            "email_id": email,
            "password": password,
        }
        count = client.privatemail.users.count_documents(mongo_filter)
        if count != 0:
            return {
                "message": "Successfully logged in user...",
            }
        else:
            raise HTTPException(status_code=404, detail="Invalid User Credentials...")
    except Exception:
        raise HTTPException(status_code=500, detail="Error login User")


@app.post("/user/create")
async def create_user(data: User):
    mongo_filter = {
        "email_id": data.email_id,
    }

    exists = client.privatemail.users.count_documents(mongo_filter)

    if exists > 0:
        raise HTTPException(status_code=400, detail="Try different id, Email already exists...")

    user_dict = {
        "id": ''.join(random.choices(string.ascii_letters, k=50)),
        "first_name": data.first_name,
        "last_name": data.last_name,
        "username": data.username,
        "email_id": data.email_id,
        "password": data.password,
        "created": f"{current_time}",
    }
    client.privatemail.users.insert_one(user_dict)
    return {
        "message": "Successfully created user...",
    }


@app.post("/user/update")
async def update_user(data: UserUpdate):
    try:
        mongo_filter = {
            "id": data.id,
        }
        updates = {
            "$set": {
                "first_name": data.first_name,
                "last_name": data.last_name,
                "username": data.username,
            }
        }
        client.privatemail.users.update_one(mongo_filter, updates)
        return {
            "message": "Successfully Updated user...",
            "data": data,
        }
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        raise HTTPException(status_code=500, detail="Error Updating User")


@app.post("/user/update/password")
async def change_password(email: str, old_password: str, new_password: str):
    mongo_filter = {
        "email_id": email,
        "password": old_password,
    }
    if_exists = client.privatemail.users.count_documents(mongo_filter)
    print(if_exists)
    if if_exists < 1:
        raise HTTPException(status_code=403, detail="Password doesn't match with old password...")

    updates = {
        "$set": {
            "password": new_password,
        }
    }
    client.privatemail.users.update_one(mongo_filter, update=updates)
    return {
        "message": "Successfully Updated user...",
    }


#######################################################################################################################
####################################         Mail Service         #####################################################
#######################################################################################################################
@app.get("/mail/get/{object_id}")
async def get_mail(object_id: str):
    try:
        pipeline = [
            {
                "$match": {
                    "id": object_id
                },
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.to_email.email_id",
                    "foreignField": "email_id",
                    "as": "sent.to_users",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.cc.email_id",
                    "foreignField": "email_id",
                    "as": "sent.cc_users",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.bcc.email_id",
                    "foreignField": "email_id",
                    "as": "sent.bcc_users",
                }
            },
            {
                "$addFields": {
                    "sent.to_users.read": "$sent.to_email.read",
                    "sent.cc_users.read": "$sent.to_email.read",
                    "sent.bcc_users.read": "$sent.to_email.read",
                }
            },
            {
                "$project": {
                    "_id": 0,

                    "sent.to_email": 0,
                    "sent.cc": 0,
                    "sent.bcc": 0,

                    "sent.to_users._id": 0,
                    "sent.to_users.first_name": 0,
                    "sent.to_users.last_name": 0,
                    "sent.to_users.password": 0,
                    "sent.to_users.created": 0,

                    "sent.cc_users._id": 0,
                    "sent.cc_users.first_name": 0,
                    "sent.cc_users.last_name": 0,
                    "sent.cc_users.password": 0,
                    "sent.cc_users.created": 0,

                    "sent.bcc_users._id": 0,
                    "sent.bcc_users.first_name": 0,
                    "sent.bcc_users.last_name": 0,
                    "sent.bcc_users.password": 0,
                    "sent.bcc_users.created": 0,
                }
            },
        ]
        data = list(client.privatemail.emails.aggregate(pipeline))
        return {
            "message": "Successfully fetched the mails.",
            "data": data
        }
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        raise HTTPException(status_code=500, detail="Error fetching mail.")


@app.get("/mail/sent/{email_id}")
async def get_sent_mails(email_id: str):
    try:
        pipe_line = [
            {
                "$match": {
                    "sent.from_email": email_id
                },
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.to_email.email_id",
                    "foreignField": "email_id",
                    "as": "sent.to_users",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.cc.email_id",
                    "foreignField": "email_id",
                    "as": "sent.cc_users",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.bcc.email_id",
                    "foreignField": "email_id",
                    "as": "sent.bcc_users",
                }
            },
            {
                "$addFields": {
                    "sent.to_users.read": "$sent.to_email.read",
                    "sent.cc_users.read": "$sent.to_email.read",
                    "sent.bcc_users.read": "$sent.to_email.read",
                }
            },
            {
                "$project": {
                    "_id": 0,

                    "sent.to_email": 0,
                    "sent.cc": 0,
                    "sent.bcc": 0,

                    "sent.to_users._id": 0,
                    "sent.to_users.first_name": 0,
                    "sent.to_users.last_name": 0,
                    "sent.to_users.password": 0,
                    "sent.to_users.created": 0,

                    "sent.cc_users._id": 0,
                    "sent.cc_users.first_name": 0,
                    "sent.cc_users.last_name": 0,
                    "sent.cc_users.password": 0,
                    "sent.cc_users.created": 0,

                    "sent.bcc_users._id": 0,
                    "sent.bcc_users.first_name": 0,
                    "sent.bcc_users.last_name": 0,
                    "sent.bcc_users.password": 0,
                    "sent.bcc_users.created": 0,
                }
            },
        ]
        data = list(client.privatemail.emails.aggregate(pipe_line))
        return {
            "message": "Successfully fetched mails...",
            "data": data
        }
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        raise HTTPException(status_code=500, detail="Error fetching mails...")


@app.get("/mail/received/{email_id}")
async def get_received_mails(email_id: str):
    try:
        pipe_line = [
            {
                "$match": {
                    "$or": [
                        {
                            "sent.to_email.email_id": {
                                "$in": [email_id],
                            }
                        },
                        {
                            "sent.cc.email_id": {
                                "$in": [email_id],
                            }
                        },
                        {
                            "sent.bcc.email_id": {
                                "$in": [email_id],
                            }
                        }
                    ]
                },
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.to_email.email_id",
                    "foreignField": "email_id",
                    "as": "sent.to_users",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.cc.email_id",
                    "foreignField": "email_id",
                    "as": "sent.cc_users",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sent.bcc.email_id",
                    "foreignField": "email_id",
                    "as": "sent.bcc_users",
                }
            },
            {
                "$addFields": {
                    "sent.to_users.read": "$sent.to_email.read",
                    "sent.cc_users.read": "$sent.to_email.read",
                    "sent.bcc_users.read": "$sent.to_email.read",
                }
            },
            {
                "$project": {
                    "_id": 0,

                    "sent.to_email": 0,
                    "sent.cc": 0,
                    "sent.bcc": 0,

                    "sent.to_users._id": 0,
                    "sent.to_users.first_name": 0,
                    "sent.to_users.last_name": 0,
                    "sent.to_users.password": 0,
                    "sent.to_users.created": 0,

                    "sent.cc_users._id": 0,
                    "sent.cc_users.first_name": 0,
                    "sent.cc_users.last_name": 0,
                    "sent.cc_users.password": 0,
                    "sent.cc_users.created": 0,

                    "sent.bcc_users._id": 0,
                    "sent.bcc_users.first_name": 0,
                    "sent.bcc_users.last_name": 0,
                    "sent.bcc_users.password": 0,
                    "sent.bcc_users.created": 0,
                }
            },
        ]
        data = list(client.privatemail.emails.aggregate(pipe_line))
        return {
            "message": "Successfully fetched mails...",
            "data": data
        }
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        raise HTTPException(status_code=500, detail="Error fetching mails...")


@app.post("/mail/send")
async def send_mail(mail: Email):
    try:
        to_email = []
        if len(mail.sent["to_email"]) > 0:
            for email in mail.sent["to_email"]:
                seen_obj = {
                    "email_id": email,
                    "read": False,
                }
                to_email.append(seen_obj)

        cc = []
        if len(mail.sent["cc"]) > 0:
            for email in mail.sent["cc"]:
                seen_obj = {
                    "email_id": email,
                    "read": False,
                }
                cc.append(seen_obj)

        bcc = []
        if len(mail.sent["bcc"]) > 0:
            for email in mail.sent["bcc"]:
                seen_obj = {
                    "email_id": email,
                    "read": False,
                }
                bcc.append(seen_obj)

        email_obj = {
            "id": ''.join(random.choices(string.ascii_letters, k=50)),
            "sent": {
                "from_email": mail.sent["from_email"],
                "to_email": to_email,
                "cc": cc,
                "bcc": bcc,
                "sent_at": current_time
            },
            "reply": {
                "reply_ids": [],
                "has_reply": False,
            },
            "subject": mail.subject,
            "body": mail.body,
        }
        client.privatemail.emails.insert_one(email_obj)
        return {
            "message": "Mail Sent!",
        }
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        raise HTTPException(status_code=500, detail="Error Sending email...")


@app.get("/mail/{object_id}/read/{email_id}")
async def mark_as_read(object_id: str, email_id: str):
    mongo_filter = {
        "id": object_id,
        "sent.to_email.email_id": email_id,
    }
    updates = {
        "$set": {
            "sent.to_email.$.read": True,
        }
    }
    client.privatemail.emails.update_one(filter=mongo_filter, update=updates)

    mongo_filter = {
        "id": object_id,
        "sent.cc.email_id": email_id,
    }
    updates = {
        "$set": {
            "sent.cc.$.read": True,
        }
    }
    client.privatemail.emails.update_one(filter=mongo_filter, update=updates)

    mongo_filter = {
        "id": object_id,
        "sent.bcc.email_id": email_id,
    }
    updates = {
        "$set": {
            "sent.bcc.$.read": True,
        }
    }
    client.privatemail.emails.update_one(filter=mongo_filter, update=updates)
    return {
        "message": "Marked Mail as read."
    }


@app.post("/mail/reply")
async def reply_mail(reply: EmailReply):
    reply_id = ''.join(random.choices(string.ascii_letters, k=50))

    mongo_filter = {
        "id": reply.parent_id
    }

    project = {
        "_id": 0,
        "reply.to_email": 0,
        "reply.replied": 0,
        "subject": 0,
        "body": 0
    }
    parent = client.privatemail.replies.find_one(mongo_filter, project)

    if parent:
        target = parent["reply"]["from_email"]

        updates = {
            "$set": {
                "reply.has_reply": True,
                "reply.reply_id": reply_id,
            },
        }
        client.privatemail.replies.update_one(mongo_filter, update=updates)
    else:
        project = {
            "_id": 0,
            "sent.to_email": 0,
            "sent.cc": 0,
            "sent.bcc": 0,
            "subject": 0,
            "body": 0
        }
        parent = client.privatemail.emails.find_one(mongo_filter, project)
        target = parent["sent"]["from_email"]

        updates = {
            "$set": {
                "reply.has_reply": True,
            },
            "$push": {
                "reply.reply_ids": [reply_id],
            }
        }
        client.privatemail.emails.update_one(mongo_filter, update=updates)

    reply_obj = {
        "id": reply_id,
        "reply": {
            "parent_id": reply.parent_id,
            "from_email": reply.from_email,
            "to_email": target,
            "replied_at": f"{current_time}",
            "reply_id": "",
            "has_reply": False
        },
        "subject": reply.subject,
        "body": reply.body,
    }
    client.privatemail.replies.insert_one(reply_obj)
    return {
        "message": "Successfully replied to message..."
    }


# @app.get("/mail/{object_id}/forward/{from_email}/to/{email_id}")
# async def forward_mail(object_id: str, from_email: str, email_id: str):
#     mongo_filter = {
#         "object_id": object_id
#     }
#     updates = {
#         "$set": {
#             "forward": [{
#                 "from_email": from_email,
#
#             }]
#         }
#     }
#     client.privatemail.emails.update_one(filter=mongo_filter, update=updates)
#     return {
#         "message": f"Forwarded mail to {email_id}"
#     }

if __name__ == "__main__":
    uvicorn.run(app_dir="./apis", app="server:app", host=HOST, port=PORT, reload=True,
                log_level="debug")
