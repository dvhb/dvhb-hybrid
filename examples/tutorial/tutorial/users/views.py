async def get_users(request):
    users = await request.app.m.user.get_list(fields=['username', 'email'])
    return users
