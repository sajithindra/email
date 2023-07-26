import uvicorn, random, string, traceback
from datetime import datetime
from models import User, UserUpdate, Email, EmailReply, EmailForward
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
'''
get_mail:
    This api is to get the detail description of an particular mail with the mail's id field in the mongodb document.
    Id is passed as a path variable
'''
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


'''
get_sent_mails:
    This api is to get the outbox of a particular person.
    email of the person is passed as a path variable.
    This api will return all the mails that are sent by the user.
'''
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


'''
get_received_mails:
    This api is to get the inbox of a particular person.
    email of the person is passed as a path variable.
    This api will return all the mails that are forwarded, replied, cc, bcc or sent to him.
'''
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


'''
send_mail:
    This api is to send the mail to the particular person
    The post request takes the mail contents as body.
    This api will create a document in an the emails collection.
'''
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
            "forward": {
                "parent_id": "",
                "is_forward": False,
                "forward_ids": [],
                "has_forwards": False,
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


'''
mark_as_read:
    This api is to mark a marticular email as read.
    The request takes the email collection's id field and email of person who read the mail as path variable
'''
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


'''
reply_mail:
    This api is to send the reply mail to the particular mail as a response.
    The post request takes the mail contents as body.
    This api will create a document in an the replies collection.
'''
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
        "forward": {
            "forward_ids": [],
            "has_forwards": False,
        },
        "subject": reply.subject,
        "body": reply.body,
    }
    client.privatemail.replies.insert_one(reply_obj)
    return {
        "message": "Successfully replied to message..."
    }


'''
forward_mail:
    This api is to forward a particular to a other person..
    The post request takes the mail contents as body.
    This api will create a document in an the replies collection.
'''
@app.post("/mail/forward")
async def forward_mail(forward: EmailForward):
    forward_id = ''.join(random.choices(string.ascii_letters, k=50))

    mongo_filter = {
        "id": forward.parent_id
    }

    project = {
        "_id": 0,
        "reply": 0,
        "subject": 0,
        "body": 0
    }
    parent_from_email = client.privatemail.emails.find_one(mongo_filter, project)
    parent_from_reply = client.privatemail.replies.find_one(mongo_filter, project)

    updates = {
        "$set": {
            "forward.has_forwards": True,
        },
        "$push": {
            "forward.forward_ids": [forward_id],
        }
    }

    if parent_from_email:
        client.privatemail.emails.update_one(mongo_filter, update=updates)
    elif parent_from_reply:
        client.privatemail.replies.update_one(mongo_filter, update=updates)
    else:
        raise HTTPException(status_code=404, detail="Unable to find Parent mail Object...")

    to_email = []
    if len(forward.sent["to_email"]) > 0:
        for email in forward.sent["to_email"]:
            seen_obj = {
                "email_id": email,
                "read": False,
            }
            to_email.append(seen_obj)

    cc = []
    if len(forward.sent["cc"]) > 0:
        for email in forward.sent["cc"]:
            seen_obj = {
                "email_id": email,
                "read": False,
            }
            cc.append(seen_obj)

    bcc = []
    if len(forward.sent["bcc"]) > 0:
        for email in forward.sent["bcc"]:
            seen_obj = {
                "email_id": email,
                "read": False,
            }
            bcc.append(seen_obj)

    forward_obj = {
        "id": forward_id,
        "sent": {
            "from_email": forward.sent["from_email"],
            "to_email": to_email,
            "cc": cc,
            "bcc": bcc,
            "sent_at": current_time
        },
        "reply": {
            "reply_ids": [],
            "has_reply": False,
        },
        "forward": {
            "parent_id": forward.parent_id,
            "is_forward": True,
            "forward_ids": [],
            "has_forwards": False,
        },
        "subject": forward.subject,
        "body": forward.body,
    }

    client.privatemail.emails.insert_one(forward_obj)
    return {
        "message": "Successfully Forwarded..."
    }


if __name__ == "__main__":
    uvicorn.run(app="server:app", host=HOST, port=PORT, reload=True,
                log_level="debug")
