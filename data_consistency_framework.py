import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class DataConsistencyValidator:
    """
    Validates data consistency for guest updates and other operations.
    """
    
    @staticmethod
    def validate_guest_data(guest, updates):
        """
        Validates guest data updates.
        Returns tuple (is_valid, errors_dict)
        """
        errors = {}
        
        # Email validation
        if 'email' in updates and updates['email']:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", updates['email']):
                errors['email'] = 'Invalid email format'
                
        # Phone validation (simple check)
        if 'phone' in updates and updates['phone']:
            # Allow digits, spaces, dashes, plus sign
            if not re.match(r"^[\d\s\-\+]+$", updates['phone']):
                errors['phone'] = 'Invalid phone number format'
                
        # Required fields check if they are being cleared (set to empty string)
        required_fields = ['first_name', 'last_name']
        for field in required_fields:
            if field in updates and not updates[field]:
                 errors[field] = 'This field cannot be empty'

        # Date validation
        if 'check_in_date' in updates and 'check_out_date' in updates:
            check_in = updates['check_in_date']
            check_out = updates['check_out_date']
            if check_in and check_out and check_out <= check_in:
                errors['check_out_date'] = 'Check-out date must be after check-in date'

        return len(errors) == 0, errors

class DataSyncManager:
    """
    Manages data synchronization and cache invalidation.
    """
    
    @staticmethod
    def invalidate_guest_cache(guest_id, room_id=None):
        """
        Invalidates cache for specific guest and optional room.
        """
        # In a real implementation this might interact with Redis or Django cache
        # For now we'll just log it
        logger.debug(f"Invalidating cache for guest {guest_id} and room {room_id}")
        pass

class AuditLogger:
    """
    Logs significant events for audit purposes.
    """
    
    @staticmethod
    def log_guest_update(guest, old_data, updates, user):
        """
        Logs details of guest record updates.
        """
        try:
            # Calculate what actually changed
            changes = {}
            for key, value in updates.items():
                if key in old_data and old_data[key] != value:
                    changes[key] = {
                        'from': str(old_data[key]),
                        'to': str(value)
                    }
            
            if changes:
                logger.info(f"AUDIT - User: {user.username} - Guest: {guest.id} ({guest.full_name}) - Changes: {changes}")
                # You could also save this to a database model like AuditLog
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
