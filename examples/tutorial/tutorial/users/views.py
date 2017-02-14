async def get_users(request):
	return await request.app.m.user.get_list(fields=['username', 'email'])
