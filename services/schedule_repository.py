"""
Schedule repository for database operations.

This module provides CRUD operations for schedules in the PostgreSQL database.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ScheduleRepository:
    """
    Repository for schedule database operations.
    
    Provides CRUD operations for schedules stored in PostgreSQL,
    replacing the previous API-based schedule fetching.
    """
    
    def __init__(self, db_connection):
        """
        Initialize schedule repository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
    
    def create_schedule(
        self,
        domain_config_id: str,
        domain: str,
        frequency: str,
        time_config: Dict[str, Any],
        profile_id: Optional[str] = None,
        enabled: bool = True
    ) -> Optional[str]:
        """
        Create a new schedule.
        
        Args:
            domain_config_id: Domain configuration ID
            domain: Domain name
            frequency: Schedule frequency (hourly, daily, weekly, monthly)
            time_config: Time configuration dict
            profile_id: Optional scan profile ID
            enabled: Whether schedule is enabled
            
        Returns:
            Schedule ID if created, None otherwise
        """
        schedule_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO schedules (
                schedule_id, domain_config_id, domain, profile_id,
                frequency, time_config, enabled, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING schedule_id
        """
        
        try:
            import json
            result = self.db.execute_query(
                query,
                (
                    schedule_id,
                    domain_config_id,
                    domain,
                    profile_id,
                    frequency,
                    json.dumps(time_config),
                    enabled
                ),
                fetch=True
            )
            
            if result:
                logger.info(f"Created schedule {schedule_id} for domain {domain}")
                return result[0]['schedule_id']
            return None
        except Exception as e:
            logger.error(f"Failed to create schedule for {domain}: {e}")
            return None
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a schedule by ID.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Schedule dict if found, None otherwise
        """
        query = """
            SELECT 
                schedule_id, domain_config_id, domain, profile_id,
                frequency, time_config, enabled, next_run, last_run,
                last_status, created_at, updated_at
            FROM schedules
            WHERE schedule_id = %s
        """
        
        try:
            result = self.db.execute_query(query, (schedule_id,), fetch=True)
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get schedule {schedule_id}: {e}")
            return None
    
    def get_all_schedules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all schedules.
        
        Args:
            enabled_only: If True, only return enabled schedules
            
        Returns:
            List of schedule dicts
        """
        query = """
            SELECT 
                schedule_id, domain_config_id, domain, profile_id,
                frequency, time_config, enabled, next_run, last_run,
                last_status, created_at, updated_at
            FROM schedules
        """
        
        if enabled_only:
            query += " WHERE enabled = TRUE"
        
        query += " ORDER BY domain, created_at"
        
        try:
            result = self.db.execute_query(query, fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get schedules: {e}")
            return []
    
    def get_schedules_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all schedules for a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            List of schedule dicts
        """
        query = """
            SELECT 
                schedule_id, domain_config_id, domain, profile_id,
                frequency, time_config, enabled, next_run, last_run,
                last_status, created_at, updated_at
            FROM schedules
            WHERE domain = %s
            ORDER BY created_at
        """
        
        try:
            result = self.db.execute_query(query, (domain,), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get schedules for domain {domain}: {e}")
            return []
    
    def update_schedule(
        self,
        schedule_id: str,
        frequency: Optional[str] = None,
        time_config: Optional[Dict[str, Any]] = None,
        profile_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        next_run: Optional[datetime] = None
    ) -> bool:
        """
        Update a schedule.
        
        Args:
            schedule_id: Schedule ID
            frequency: New frequency (optional)
            time_config: New time configuration (optional)
            profile_id: New profile ID (optional)
            enabled: New enabled status (optional)
            next_run: New next run time (optional)
            
        Returns:
            True if updated, False otherwise
        """
        # Build dynamic update query
        updates = []
        params = []
        
        if frequency is not None:
            updates.append("frequency = %s")
            params.append(frequency)
        
        if time_config is not None:
            import json
            updates.append("time_config = %s")
            params.append(json.dumps(time_config))
        
        if profile_id is not None:
            updates.append("profile_id = %s")
            params.append(profile_id)
        
        if enabled is not None:
            updates.append("enabled = %s")
            params.append(enabled)
        
        if next_run is not None:
            updates.append("next_run = %s")
            params.append(next_run)
        
        if not updates:
            logger.warning(f"No updates provided for schedule {schedule_id}")
            return False
        
        updates.append("updated_at = NOW()")
        params.append(schedule_id)
        
        query = f"""
            UPDATE schedules
            SET {', '.join(updates)}
            WHERE schedule_id = %s
        """
        
        try:
            self.db.execute_query(query, tuple(params), fetch=False)
            logger.info(f"Updated schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update schedule {schedule_id}: {e}")
            return False
    
    def update_schedule_run_status(
        self,
        schedule_id: str,
        last_run: datetime,
        next_run: Optional[datetime] = None,
        status: str = 'success'
    ) -> bool:
        """
        Update schedule run status after execution.
        
        Args:
            schedule_id: Schedule ID
            last_run: Last run timestamp
            next_run: Next run timestamp (optional)
            status: Execution status (success, failed)
            
        Returns:
            True if updated, False otherwise
        """
        query = """
            UPDATE schedules
            SET last_run = %s, next_run = %s, last_status = %s, updated_at = NOW()
            WHERE schedule_id = %s
        """
        
        try:
            self.db.execute_query(
                query,
                (last_run, next_run, status, schedule_id),
                fetch=False
            )
            logger.debug(f"Updated run status for schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update run status for schedule {schedule_id}: {e}")
            return False
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            True if deleted, False otherwise
        """
        query = "DELETE FROM schedules WHERE schedule_id = %s"
        
        try:
            self.db.execute_query(query, (schedule_id,), fetch=False)
            logger.info(f"Deleted schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete schedule {schedule_id}: {e}")
            return False
    
    def sync_from_api(self, api_schedules: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sync schedules from API to database.
        
        This method reconciles schedules from the API with the database,
        creating new schedules and updating existing ones.
        
        Args:
            api_schedules: List of schedule dicts from API
            
        Returns:
            Dict with counts of created, updated, and skipped schedules
        """
        stats = {'created': 0, 'updated': 0, 'skipped': 0}
        
        for api_schedule in api_schedules:
            try:
                domain_config_id = api_schedule.get('domain_config_id')
                domain_data = api_schedule.get('data', {})
                domain = domain_data.get('domain', '')
                schedule_cfg = domain_data.get('schedule', {})
                
                if not domain or not domain_config_id:
                    stats['skipped'] += 1
                    continue
                
                # Check if schedule already exists for this domain_config_id
                existing = self.get_schedules_by_domain_config_id(domain_config_id)
                
                frequency = schedule_cfg.get('frequency', '').lower()
                time_config = schedule_cfg.get('time', {})
                
                if existing:
                    # Update existing schedule
                    schedule_id = existing[0]['schedule_id']
                    self.update_schedule(
                        schedule_id,
                        frequency=frequency,
                        time_config=time_config
                    )
                    stats['updated'] += 1
                else:
                    # Create new schedule
                    self.create_schedule(
                        domain_config_id=domain_config_id,
                        domain=domain,
                        frequency=frequency,
                        time_config=time_config,
                        enabled=True
                    )
                    stats['created'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync schedule for {domain}: {e}")
                stats['skipped'] += 1
        
        logger.info(
            f"Schedule sync completed: "
            f"{stats['created']} created, {stats['updated']} updated, "
            f"{stats['skipped']} skipped"
        )
        return stats
    
    def get_schedules_by_domain_config_id(
        self,
        domain_config_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get schedules by domain config ID.
        
        Args:
            domain_config_id: Domain configuration ID
            
        Returns:
            List of schedule dicts
        """
        query = """
            SELECT 
                schedule_id, domain_config_id, domain, profile_id,
                frequency, time_config, enabled, next_run, last_run,
                last_status, created_at, updated_at
            FROM schedules
            WHERE domain_config_id = %s
            ORDER BY created_at
        """
        
        try:
            result = self.db.execute_query(query, (domain_config_id,), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(
                f"Failed to get schedules for domain_config_id {domain_config_id}: {e}"
            )
            return []


# Singleton instance
_schedule_repository: Optional[ScheduleRepository] = None


def get_schedule_repository() -> ScheduleRepository:
    """Get the global schedule repository instance."""
    global _schedule_repository
    if _schedule_repository is None:
        raise RuntimeError(
            "Schedule repository not initialized. Call init_schedule_repository() first."
        )
    return _schedule_repository


def init_schedule_repository(db_connection) -> ScheduleRepository:
    """Initialize the global schedule repository instance."""
    global _schedule_repository
    _schedule_repository = ScheduleRepository(db_connection)
    return _schedule_repository
