async def get_user_id(username: str):
    # ensure that the username fits the minimum length requirement
    try:
        if len(username) <= 5:
            return None
    except ValueError:
        return "Invalid data type for string username."

    if username.startswith("@"):
        username = username[1:]
    
    return # will need to find a way to get the user id based on username
