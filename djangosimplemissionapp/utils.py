from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q

def get_date_filter_q(filter_type, date_field='start_date', start_date_str=None, end_date_str=None):
    """
    Returns a Django Q object for date filtering based on common ranges.
    """
    today = timezone.now().date()
    filter_type = (filter_type or 'today').lower()
    
    if filter_type == 'all':
        return Q()

    if filter_type == 'today':
        return Q(**{f'{date_field}': today})
    
    elif filter_type == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return Q(**{f'{date_field}__range': [start_of_week, end_of_week]})
    
    elif filter_type == 'this_month':
        start_of_month = today.replace(day=1)
        if today.month == 12:
            end_of_month = start_of_month.replace(year=today.year + 1, month=1) - timedelta(days=1)
        else:
            end_of_month = start_of_month.replace(month=today.month + 1) - timedelta(days=1)
        return Q(**{f'{date_field}__range': [start_of_month, end_of_month]})
    
    elif filter_type == 'this_year':
        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)
        return Q(**{f'{date_field}__range': [start_of_year, end_of_year]})
    
    elif filter_type == 'custom':
        if not start_date_str or not end_date_str:
            return None, "For custom filter, both start_date and end_date are required (format: YYYY-MM-DD)"
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date > end_date:
                return None, "start_date must be before end_date"
            
            return Q(**{f'{date_field}__range': [start_date, end_date]}), None
        except ValueError:
            return None, "Invalid date format. Please use YYYY-MM-DD"
    
    return Q(), "Invalid filter type"
def calculate_performance_metrics(activities):
    """
    Calculates average progress, target progress, and efficiency from a list of activities.
    """
    total = len(activities)
    if total == 0:
        return {
            "avg_progress": 0,
            "avg_target": 0,
            "efficiency": 0,
            "total_activities": 0
        }
    
    actual_sum = sum(100 - (a.pending_work_percentage or 0) for a in activities)
    target_sum = sum(getattr(a, 'target_work_percentage', 0) for a in activities)
    
    avg_progress = float(actual_sum) / total
    avg_target = float(target_sum) / total
    efficiency = (float(actual_sum) / float(target_sum) * 100) if target_sum > 0 else 0
    
    return {
        "avg_progress": round(avg_progress, 2),
        "avg_target": round(avg_target, 2),
        "efficiency": round(efficiency, 2),
        "total_activities": total
    }


def get_client_ip(request):
    """
    Extract client IP address from request, handling proxy headers.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    """
    Parse user agent string to extract device, browser, and OS information.
    Returns a dictionary with device details.
    """
    device_info = {
        'device_type': 'Desktop',
        'device_name': None,
        'browser_name': None,
        'browser_version': None,
        'os_name': None,
        'os_version': None,
    }
    
    if not user_agent_string:
        return device_info
    
    ua = user_agent_string.lower()
    
    # Detect Device Type
    if 'mobile' in ua or 'android' in ua:
        device_info['device_type'] = 'Mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        device_info['device_type'] = 'Tablet'
    elif 'windows' in ua or 'macintosh' in ua or 'linux' in ua:
        device_info['device_type'] = 'Desktop'
    
    # Detect OS
    if 'windows' in ua:
        device_info['os_name'] = 'Windows'
        # Extract version
        if 'nt 10.0' in ua:
            device_info['os_version'] = '10'
        elif 'nt 6.3' in ua:
            device_info['os_version'] = '8.1'
        elif 'nt 6.2' in ua:
            device_info['os_version'] = '8'
    elif 'macintosh' in ua:
        device_info['os_name'] = 'macOS'
        if 'mac os x' in ua:
            import re
            match = re.search(r'mac os x ([\d_]+)', ua)
            if match:
                device_info['os_version'] = match.group(1).replace('_', '.')
    elif 'iphone' in ua:
        device_info['os_name'] = 'iOS'
        device_info['device_name'] = 'iPhone'
        import re
        match = re.search(r'os ([\d_]+)', ua)
        if match:
            device_info['os_version'] = match.group(1).replace('_', '.')
    elif 'ipad' in ua:
        device_info['os_name'] = 'iOS'
        device_info['device_name'] = 'iPad'
    elif 'android' in ua:
        device_info['os_name'] = 'Android'
        import re
        match = re.search(r'android ([\d.]+)', ua)
        if match:
            device_info['os_version'] = match.group(1)
    elif 'linux' in ua:
        device_info['os_name'] = 'Linux'
    
    # Detect Browser
    if 'edg' in ua:
        device_info['browser_name'] = 'Edge'
        import re
        match = re.search(r'edg/([\d.]+)', ua)
        if match:
            device_info['browser_version'] = match.group(1)
    elif 'chrome' in ua:
        device_info['browser_name'] = 'Chrome'
        import re
        match = re.search(r'chrome/([\d.]+)', ua)
        if match:
            device_info['browser_version'] = match.group(1)
    elif 'safari' in ua and 'chrome' not in ua:
        device_info['browser_name'] = 'Safari'
        import re
        match = re.search(r'version/([\d.]+)', ua)
        if match:
            device_info['browser_version'] = match.group(1)
    elif 'firefox' in ua:
        device_info['browser_name'] = 'Firefox'
        import re
        match = re.search(r'firefox/([\d.]+)', ua)
        if match:
            device_info['browser_version'] = match.group(1)
    elif 'trident' in ua:
        device_info['browser_name'] = 'Internet Explorer'
    
    return device_info


def record_user_login(user, request, login_status='SUCCESS', notes=None):
    """
    Record a user login attempt in the LoginUserDetails model.
    """
    from .models import LoginUserDetails
    
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    device_info = parse_user_agent(user_agent)
    
    login_detail = LoginUserDetails.objects.create(
        user=user,
        ip_address=ip_address,
        device_type=device_info['device_type'],
        device_name=device_info['device_name'],
        browser_name=device_info['browser_name'],
        browser_version=device_info['browser_version'],
        os_name=device_info['os_name'],
        os_version=device_info['os_version'],
        user_agent=user_agent,
        login_status=login_status,
        notes=notes,
    )
    
    return login_detail


def record_user_logout(user):
    """
    Record a user logout by updating the most recent active login record.
    Sets logout_time to now, which automatically calculates session_duration via model save().
    """
    from .models import LoginUserDetails
    from django.utils import timezone
    
    # Find the most recent active login record (no logout_time set)
    active_login = LoginUserDetails.objects.filter(
        user=user,
        logout_time__isnull=True
    ).order_by('-login_time').first()
    
    if active_login:
        active_login.logout_time = timezone.now()
        active_login.save()
        return active_login
    
    return None
