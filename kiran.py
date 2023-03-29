from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import adal
import requests
import uuid
from azure.cosmos import CosmosClient, PartitionKey,exceptions
from typing import List


app = FastAPI()
router = APIRouter()

# Set up CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure AD authentication parameters
tenant_id = '1e413fb5-14bf-4105-9723-859a37c266ef'
client_id = 'c032bfd0-e1d8-44ba-9e7b-b67bdf61caad'
client_secret = 'AlT8Q~6cNQ6~yRiwxmGI3sw3HWUF7SThTB6o9cJw'
resource = 'https://graph.microsoft.com/'

# Authenticate and get access token
authority_url = 'https://login.microsoftonline.com/' + tenant_id
context = adal.AuthenticationContext(authority_url)
token = context.acquire_token_with_client_credentials(resource, client_id, client_secret)

# Define the User model
class User(BaseModel):
    id: str
    name: str
    email: str
    age: int

# Initialize the Cosmos DB client
endpoint = "https://cosmos-part.documents.azure.com:443/"
key = "Gdh1TK7jhmB8zQGrVJ9MkNfUdXm2CLAUHk2zVAgifi0BRabIkbPih5mN8UGJ0ErKOA4oUElRVmZdACDbtRhRmQ=="
client = CosmosClient(endpoint, key)
database_name = 'ToDoList'
database = client.get_database_client(database_name)
container_name = 'Items'
container = database.get_container_client(container_name)

# # Define the endpoint to create a new user
# @router.post("/users", response_model=User)
# async def create_user(user: User):
#     item = user.dict()
#     item["id"] = str(uuid.uuid4())
#     await container.create_item(item=item)
#     return item

# Define the endpoint to fetch user details by name
@router.get('/users/{name}')
async def get_user_details(name: str):
    # Fetch user data from Microsoft Graph API
    headers = {'Authorization': 'Bearer ' + token['accessToken']}
    params = {
        '$select': 'displayName,givenName,id,mail,userType,userPrincipalName',
        '$filter':'startswith(displayName,\''+name+'\')'

    }
    response = requests.get('https://graph.microsoft.com/v1.0/users', headers=headers, params=params)

    # Process the response and return the required fields
    if response.status_code == 200:
        user_data = response.json()
        return user_data
        #return {"message": "User not found."}
    else:
        return {"message": "Error fetching user data."}
    

@router.get('/users/id/{id}')
async def get_user_details(id: str):
    # Fetch user data from Microsoft Graph API
    headers = {'Authorization': 'Bearer ' + token['accessToken']}
    params = {
        '$select': 'displayName,givenName,mail,userType,userPrincipalName',
    }
    response = requests.get(f'https://graph.microsoft.com/v1.0/users/{id}', headers=headers, params=params)

    # Process the response and return the required fields
    if response.status_code == 200:
        user_data = response.json()
        return user_data
    else:
        return {"message": "Error fetching user data."}
    

# @router.get('/users/mail/{mail}')
# async def get_user_details(mail: str):
#     # Fetch user data from Microsoft Graph API
#     headers = {'Authorization': 'Bearer ' + token['accessToken']}
#     params = {
#         '$select': 'displayName,givenName,id,userType,userPrincipalName',
#     }
#     response = requests.get(f'https://graph.microsoft.com/v1.0/users/{mail}', headers=headers, params=params)

#     print(response.status_code)
#     # Process the response and return the required fields
#     if response.status_code == 200:
#         user_data = response.json()
#         return user_data
#     else:
#         return {"message": "Error fetching user data."}

@router.get('/users/mail/{email}')
async def get_user_details(email: str):
    # Fetch user data from Microsoft Graph API
    headers = {'Authorization': 'Bearer ' + token['accessToken']}
    params = {
        '$select': 'displayName,givenName,mail,id,userType,userPrincipalName',
        '$filter': f'mail eq \'{email}\''
    }
    response = requests.get('https://graph.microsoft.com/v1.0/users', headers=headers, params=params)

    # Process the response and return the required fields
    if response.status_code == 200:
        user_data = response.json()['value']
        if len(user_data) > 0:
            return user_data[0]
        else:
            return {"message": "User not found."}
    else:
        return {"message": "Error fetching user data."}




app.include_router(router)

# Pydantic models
class Phone(BaseModel):
    Mobile: str

class ExternalId(BaseModel):
    AD: str

class UserProfile(BaseModel):
    id: str
    firstName: str
    lastName: str
    jobTitle: str
    email: str
    phones: Phone
    scopes: List[str]

# @app.get("/api/users/")
# async def get_users_by_first_name(first_name: str,response_model=List[User]):
#     try:
#         query = f"SELECT * FROM c WHERE c.firstName = '{first_name}'"
#         container_client = client.get_database_client(database_name).get_container_client(container_name)
#         items = container_client.query_items(query, enable_cross_partition_query=True)

#         UserProfile = []
#         for item in items:
#             UserProfile.append(item)
        
#         return {"users": users}
    
#     except exceptions.CosmosHttpResponseError as e:
#         return {"error": str(e)}
    

# @app.get("/api/users/")
# async def get_users_by_name(firstName: str, lastName: str):
#     query = f"SELECT * FROM c WHERE c.firstName = '{firstName}' AND c.lastName = '{lastName}'"
#     results = container.query_items(query=query, partition_key=PartitionKey.all())
#     users = [item for item in results]
#     return users

@router.get("/api/users/", response_model=List[UserProfile])
async def get_users_by_name(first_name: str = None, last_name: str = None,full_name: str = None):
    
    if first_name and last_name:
        query = f"SELECT * FROM c WHERE c.firstName = '{first_name}' AND c.lastName = '{last_name}'"
    elif full_name:
        query = f"SELECT * FROM c WHERE c.fullName = '{full_name}'" 
    elif first_name:
        query = f"SELECT * FROM c WHERE c.firstName = '{first_name}'"
    elif last_name:
        query = f"SELECT * FROM c WHERE c.lastName = '{last_name}'"
    else:
        return {"message": "Please provide a search parameter."}
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    return items

@router.get("/api/users/id/{id}", response_model=UserProfile)
async def get_user_by_id(id: str):
    query = f"SELECT * FROM c WHERE c.id = '{id}'" 
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items:
        return items[0]
    else:
        raise HTTPException(status_code=404, detail="User not found")
    
@router.get("/api/users/mail/{mail}", response_model=UserProfile)
async def get_user_by_mail(mail: str):
    query = f"SELECT * FROM c WHERE c.email = '{mail}'" 
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items:
        return items[0]
    else:
        raise HTTPException(status_code=404, detail="User not found")

app.include_router(router)