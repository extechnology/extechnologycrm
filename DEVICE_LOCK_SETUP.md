# Device-Lock Feature Implementation Guide

## Overview
This implementation adds device-level access control to your Django application. Users can be restricted to login only from approved devices using device ID tracking with admin approval workflow.

---

## Features Implemented

### 1. **Device Model** (`models.py`)
- Tracks user devices with unique device ID (MAC address, hardware ID, etc.)
- Stores device metadata (name, type, OS, browser info)
- Admin approval workflow for new devices
- Login tracking (last login, login count)

**Fields:**
- `user` - ForeignKey to User
- `device_id` - Unique device identifier
- `device_name` - User-friendly name (e.g., "My MacBook")
- `device_type` - laptop, mobile, tablet, desktop, other
- `is_approved` - Boolean approval status
- `approved_by` - Admin who approved the device
- `approved_at` - Approval timestamp
- `approval_reason` - Reason for approval/rejection
- `last_login` - Last login timestamp
- `login_count` - Total login count
- `device_info` - JSON field for additional metadata

---

## API Endpoints

### User Device Management

#### 1. **List/Register Devices**
```
POST /api/devices/
GET /api/devices/
```

**POST - Register a new device:**
```json
{
  "device_id": "AA-BB-CC-DD-EE-FF",
  "device_name": "My MacBook Pro",
  "device_type": "laptop",
  "device_info": {
    "os": "macOS",
    "browser": "Chrome",
    "version": "120.0"
  }
}
```

**Response:**
```json
{
  "message": "Device registered successfully",
  "device": {
    "id": 1,
    "device_id": "AA-BB-CC-DD-EE-FF",
    "device_name": "My MacBook Pro",
    "device_type": "laptop",
    "is_approved": false,
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

**GET - List all devices for current user:**
```
/api/devices/
```

---

#### 2. **Device Detail (Update/Delete)**
```
GET /api/devices/{id}/
PUT /api/devices/{id}/
DELETE /api/devices/{id}/
```

**PUT - Update device info:**
```json
{
  "device_name": "New Device Name",
  "device_info": {"updated": "data"}
}
```

**DELETE - Remove a device:**
```
DELETE /api/devices/{id}/
```
*Note: Users must have at least one device registered*

---

### Admin Device Approval

#### 3. **Approve/Reject Devices**
```
POST /api/devices/{device_id}/approve/
```

**Request:**
```json
{
  "action": "approve",
  "reason": "Device verified"
}
```

**Or to reject:**
```json
{
  "action": "reject",
  "reason": "Unauthorized device"
}
```

**Response:**
```json
{
  "message": "Device approved successfully",
  "device": {
    "id": 1,
    "is_approved": true,
    "approved_at": "2024-01-15T11:00:00Z",
    "approved_by": "admin_username"
  }
}
```

---

#### 4. **View Pending Approvals**
```
GET /api/admin/pending-devices/
```

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "user": 10,
      "user_username": "john_doe",
      "device_name": "iPhone 14",
      "device_type": "mobile",
      "is_approved": false,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

## Login Flow with Device Verification

### Login Request
```
POST /api/token/
Content-Type: application/json

{
  "username": "john_doe",
  "password": "password123",
  "device_id": "AA-BB-CC-DD-EE-FF",
  "device_name": "My MacBook Pro",
  "device_type": "laptop",
  "device_info": {
    "os": "macOS",
    "browser": "Chrome"
  }
}
```

### Login Scenarios

#### Scenario 1: First Device (Auto-Approved)
- User logs in with a new device_id for the first time
- Device is **automatically approved**
- Login succeeds, JWT token is issued

#### Scenario 2: New Device (Requires Approval)
- User already has approved devices
- User tries to login from a new device_id
- **Error Response**: Device not registered/pending approval
- Admin must approve device before user can login

#### Scenario 3: Approved Device
- User logs in with an approved device_id
- Device `last_login` and `login_count` are updated
- Login succeeds normally

#### Scenario 4: No Device-Lock
- User has no approved devices (first login ever)
- Can login without device_id
- First device auto-registers and auto-approves

---

## Device Approval Workflow

```
┌─────────────────┐
│ User Registers  │
└────────┬────────┘
         │
         ├─── First Device ──→ Auto-Approved ──→ Can Login
         │
         └─── Has Approved Devices ──→ New Device ──→ PENDING
                                              │
                                              ↓
                                       Admin Reviews
                                              │
                                    ┌─────────┴─────────┐
                                    │                   │
                                 Approve          Reject
                                    │                   │
                                    ↓                   ↓
                              User Can Login    Cannot Login
```

---

## Database Queries

### Get all pending device approvals
```python
from djangosimplemissionapp.models import Device
pending = Device.objects.filter(is_approved=False)
```

### Get user's devices
```python
user = User.objects.get(username='john_doe')
devices = user.devices.all()
approved = user.devices.filter(is_approved=True)
```

### Approve a device
```python
device = Device.objects.get(id=1)
admin_user = User.objects.get(username='admin')
device.approve(admin_user, reason="Verified device")
```

### Get login history
```python
device = Device.objects.get(id=1)
print(f"Last login: {device.last_login}")
print(f"Total logins: {device.login_count}")
```

---

## Permissions

New permissions added for device management:

```python
# In Django admin or API
'djangosimplemissionapp.manage_device_approvals'  # Approve/reject devices
'djangosimplemissionapp.view_all_devices'          # View all user devices (admin only)
```

---

## Frontend Integration Example

### 1. Get User's Devices
```javascript
// Fetch devices for current user
fetch('/api/devices/', {
  headers: { 'Authorization': 'Bearer ' + accessToken }
})
.then(r => r.json())
.then(data => console.log(data.results))
```

### 2. Register New Device
```javascript
async function registerDevice() {
  const response = await fetch('/api/devices/', {
    method: 'POST',
    headers: { 
      'Authorization': 'Bearer ' + accessToken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      device_id: navigator.hardwareInfo?.deviceId || 'generated-id',
      device_name: 'My Browser Device',
      device_type: 'desktop',
      device_info: {
        os: navigator.platform,
        browser: navigator.userAgent
      }
    })
  });
  return await response.json();
}
```

### 3. Login with Device
```javascript
async function loginWithDevice(username, password, deviceId) {
  const response = await fetch('/api/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: username,
      password: password,
      device_id: deviceId,
      device_name: 'My Device',
      device_type: 'desktop'
    })
  });
  const data = await response.json();
  
  if (response.ok) {
    localStorage.setItem('accessToken', data.access);
    return data;
  } else {
    // Handle device approval required
    if (data.detail?.includes('not approved')) {
      alert('Please wait for admin to approve this device');
    }
    throw new Error(data.detail || 'Login failed');
  }
}
```

### 4. Admin Approve Device
```javascript
async function approveDevice(deviceId, reason) {
  const response = await fetch(`/api/devices/${deviceId}/approve/`, {
    method: 'POST',
    headers: { 
      'Authorization': 'Bearer ' + adminToken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      action: 'approve',
      reason: reason
    })
  });
  return await response.json();
}
```

---

## Important Notes

1. **First Device is Auto-Approved**: User's first device is automatically approved to enable first-time login without admin intervention

2. **Device ID Must Be Unique**: Each device should have a unique identifier (MAC address recommended)

3. **Minimum One Device**: Users cannot delete all their devices - must have at least one

4. **Admin Permissions Required**: Only users with `manage_device_approvals` permission can approve/reject devices

5. **Login Failure Messages**: 
   - Device not registered: "This device is not registered. Please register this device first..."
   - Device not approved: "This device is not approved. Please contact your administrator..."

6. **Device Metadata**: The `device_info` JSON field can store any additional information (browser, OS, IP, etc.)

---

## Testing

### Test Device Registration
```bash
curl -X POST http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-123",
    "device_name": "Test Device",
    "device_type": "laptop"
  }'
```

### Test Login with Device
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "device_id": "test-device-123",
    "device_name": "Test Device",
    "device_type": "laptop"
  }'
```

### Test Device Approval
```bash
curl -X POST http://localhost:8000/api/devices/1/approve/ \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "reason": "Device verified"
  }'
```

---

## Troubleshooting

### Device login fails with "device_id_required"
- User has approved devices but didn't send device_id in login request
- Solution: Always send device_id when user has multiple approved devices

### Device can't be deleted
- Users must keep at least one device
- Solution: Register another device first, then delete the old one

### Admin can't see pending devices
- Admin user doesn't have `manage_device_approvals` permission
- Solution: Grant permission via Django admin or programmatically

---

## Future Enhancements

1. Device geolocation tracking
2. Device security score calculation
3. Suspicious login detection
4. Device remote wipe capability
5. Biometric authentication per device
6. IP whitelist management
7. Device expiration and forced re-registration

---

## Summary

Your Django application now has:
✅ Device registration and management  
✅ Admin approval workflow  
✅ Device tracking (login count, last login)  
✅ Automatic first-device approval  
✅ User-friendly device names and types  
✅ Device lock enforcement on login  
✅ Complete API endpoints for all operations  
✅ Permission-based access control
