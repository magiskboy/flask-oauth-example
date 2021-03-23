# Simple blog application

### API documentation

| Name                         | URL                    | Method | Token? | Body                                      | Params                                                                 | Response                                                                                                                                           |
|------------------------------|------------------------|--------|--------|-------------------------------------------|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Login or Register            | /auth                  | GET    | No     |                                           | provider: "google" \| "facebook" action: "login" \| "register"         | OAuth2 flow                                                                                                                                        |
| Logout                       | /auth/logout           | GET    | Yes    |                                           |                                                                        | {"message": string}                                                                                                                                |
| Callback in OAuth2 flow      | /auth/callback         | GET    | No     |                                           | code: string state: string of json, which includes provider and action | login: {"access_token": string} register: {"message": string}                                                                                      |
| Link account to the provider | /link_account          | GET    | Yes    |                                           | access_token: string provider: "google" \| "facebook"                  |                                                                                                                                                    |
| Get list post                | /posts                 | GET    | No     |                                           | author_id?: integer                                                    | {"posts": [{    "id": integer,   "title": string,   "summary": string,   "author_id": integer,   "author_name": string,   "like_string": string}]} |
| Get the specify post         | /posts/<post_id>       | GET    | No     |                                           | post_id: integer                                                       | {"data":{"id": integer,"title": string, "body": string,"author_id": integer,"author_name": string,"like_string": string}}                          |
| Get likes of the post        | /posts/<post_id>/likes | GET    | No     |                                           | post_id: integer                                                       | {"users": [{"id": integer, "name": string}]}                                                                                                       |
| Create new post              | /posts                 | POST   | Yes    | {    "title": string,    "body": string } |                                                                        | {"message": string, "data": {"id": integer}}                                                                                                       |


### Notice before run?

Application needs some environments:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- FACEBOOK_CLIENT_ID
- FACEBOOK_CLIENT_SECRET

and need to export FLASK_ENV=development for development env

### Run with docker-compose

Consider docker-compose.yml before execute following commands

```sh
$ docker-compose up -d
```


### Run without docker-compose

```sh
$ virtualenv env
$ source env/bin/activate
$ FLASK_ENV=development FLASK_APP=wsgi:app <google and facebook key> flask run
```
