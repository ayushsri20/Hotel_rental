# Credentials Reference

## Production (Railway Deployment)

### Admin Access
- **URL**: https://web-production-38bb.up.railway.app/login/
- **Username**: `ayush`
- **Password**: `admin123`
- **Email**: admin@example.com

### Django Admin Panel
- **URL**: https://web-production-38bb.up.railway.app/admin/
- **Username**: `ayush`
- **Password**: `admin123`

## Local Development

### Multiple Admin Users Available
The local SQLite database contains several test users:

1. **admin** (Superuser)
   - Email: admin@gmail.com
   - Is Staff: Yes
   - Is Superuser: Yes

2. **ayush** (Superuser)
   - Email: admin@gmail.com
   - Is Staff: Yes
   - Is Superuser: Yes

3. **admin_test** (Superuser)
   - Email: admin@test.com
   - Is Staff: No
   - Is Superuser: Yes

4. **testadmin** (Superuser)
   - Email: test@example.com
   - Is Staff: Yes
   - Is Superuser: Yes

5. **tdashadmin** (Staff)
   - Email: (none)
   - Is Staff: Yes
   - Is Superuser: No

6. **testuser** (Regular User)
   - Email: testuser@example.com
   - Is Staff: No
   - Is Superuser: No

> **Note**: Local development passwords may vary. Check with the development team if you need access to local test accounts.

## Security Notes

> [!WARNING]
> **Production Security**: The current production credentials are simple for development/testing purposes. Before going live with real users:
> 1. Change the admin password to a strong, unique password
> 2. Update the email to a real administrative email address
> 3. Enable two-factor authentication if available
> 4. Regularly rotate credentials

## Credential Management

### Changing Production Password

To change the production admin password:

1. Log in to the Railway dashboard
2. Open a shell session or use Django admin
3. Run:
   ```python
   from django.contrib.auth.models import User
   user = User.objects.get(username='ayush')
   user.set_password('your_new_secure_password')
   user.save()
   ```

### Creating Additional Admin Users

To create additional admin users in production:

1. Access Railway shell or Django admin
2. Run:
   ```python
   from django.contrib.auth.models import User
   User.objects.create_superuser('new_username', 'email@example.com', 'secure_password')
   ```

## Deployment Script

The production superuser is automatically created during Railway deployment via `railway_release.sh`:

```bash
python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='ayush').exists():
    User.objects.create_superuser('ayush', 'admin@example.com', 'admin123')
    print('✓ Superuser created')
else:
    print('✓ Superuser already exists')
"
```

This ensures the admin account exists even after database resets or fresh deployments.
