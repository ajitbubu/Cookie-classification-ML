"""
Scan profile service for CRUD operations.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

import asyncpg
from pydantic import ValidationError

from src.models.profile import ScanProfile, ScanProfileCreate, ScanProfileUpdate
from src.core.config import get_config

logger = logging.getLogger(__name__)
settings = get_config()


class ProfileService:
    """Service for managing scan profiles."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize profile service with database pool."""
        self.db_pool = db_pool
    
    async def create_profile(
        self,
        profile_data: ScanProfileCreate,
        created_by: Optional[UUID] = None
    ) -> ScanProfile:
        """
        Create a new scan profile.
        
        Args:
            profile_data: Profile creation data
            created_by: UUID of user creating the profile
            
        Returns:
            Created ScanProfile
        """
        profile_id = uuid4()
        now = datetime.utcnow()
        
        # Build config dict from profile data
        config = {
            'max_depth': profile_data.max_depth,
            'max_pages': profile_data.max_pages,
            'max_retries': profile_data.max_retries,
            'custom_pages': profile_data.custom_pages,
            'accept_button_selector': profile_data.accept_button_selector,
            'wait_for_dynamic_content': profile_data.wait_for_dynamic_content,
            'follow_external_links': profile_data.follow_external_links,
            'collect_screenshots': profile_data.collect_screenshots,
            'user_agent': profile_data.user_agent,
            'viewport': profile_data.viewport
        }
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scan_profiles (
                    profile_id, name, scan_mode, config, created_by, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                profile_id,
                profile_data.name,
                profile_data.scan_mode,
                config,
                created_by,
                now,
                now
            )
            
            return self._row_to_profile(row)
    
    async def get_profile(self, profile_id: UUID) -> Optional[ScanProfile]:
        """
        Get a scan profile by ID.
        
        Args:
            profile_id: Profile UUID
            
        Returns:
            ScanProfile if found, None otherwise
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM scan_profiles WHERE profile_id = $1",
                profile_id
            )
            
            if row:
                return self._row_to_profile(row)
            return None
    
    async def list_profiles(
        self,
        scan_mode: Optional[str] = None,
        created_by: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ScanProfile]:
        """
        List scan profiles with optional filtering.
        
        Args:
            scan_mode: Filter by scan mode
            created_by: Filter by creator
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of ScanProfile objects
        """
        query = "SELECT * FROM scan_profiles WHERE 1=1"
        params = []
        param_count = 0
        
        if scan_mode:
            param_count += 1
            query += f" AND scan_mode = ${param_count}"
            params.append(scan_mode)
        
        if created_by:
            param_count += 1
            query += f" AND created_by = ${param_count}"
            params.append(created_by)
        
        query += " ORDER BY created_at DESC"
        
        param_count += 1
        query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        query += f" OFFSET ${param_count}"
        params.append(offset)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_profile(row) for row in rows]
    
    async def update_profile(
        self,
        profile_id: UUID,
        profile_data: ScanProfileUpdate
    ) -> Optional[ScanProfile]:
        """
        Update a scan profile.
        
        Args:
            profile_id: Profile UUID
            profile_data: Profile update data
            
        Returns:
            Updated ScanProfile if found, None otherwise
        """
        # Get existing profile
        existing = await self.get_profile(profile_id)
        if not existing:
            return None
        
        # Build update dict with only provided fields
        update_fields = {}
        if profile_data.name is not None:
            update_fields['name'] = profile_data.name
        if profile_data.scan_mode is not None:
            update_fields['scan_mode'] = profile_data.scan_mode
        
        # Update config fields
        config = existing.config.copy()
        if profile_data.max_depth is not None:
            config['max_depth'] = profile_data.max_depth
        if profile_data.max_pages is not None:
            config['max_pages'] = profile_data.max_pages
        if profile_data.max_retries is not None:
            config['max_retries'] = profile_data.max_retries
        if profile_data.custom_pages is not None:
            config['custom_pages'] = profile_data.custom_pages
        if profile_data.accept_button_selector is not None:
            config['accept_button_selector'] = profile_data.accept_button_selector
        if profile_data.wait_for_dynamic_content is not None:
            config['wait_for_dynamic_content'] = profile_data.wait_for_dynamic_content
        if profile_data.follow_external_links is not None:
            config['follow_external_links'] = profile_data.follow_external_links
        if profile_data.collect_screenshots is not None:
            config['collect_screenshots'] = profile_data.collect_screenshots
        if profile_data.user_agent is not None:
            config['user_agent'] = profile_data.user_agent
        if profile_data.viewport is not None:
            config['viewport'] = profile_data.viewport
        
        update_fields['config'] = config
        update_fields['updated_at'] = datetime.utcnow()
        
        # Build dynamic update query
        set_clauses = []
        params = []
        param_count = 0
        
        for field, value in update_fields.items():
            param_count += 1
            set_clauses.append(f"{field} = ${param_count}")
            params.append(value)
        
        param_count += 1
        params.append(profile_id)
        
        query = f"""
            UPDATE scan_profiles
            SET {', '.join(set_clauses)}
            WHERE profile_id = ${param_count}
            RETURNING *
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                return self._row_to_profile(row)
            return None
    
    async def delete_profile(self, profile_id: UUID) -> bool:
        """
        Delete a scan profile.
        
        Args:
            profile_id: Profile UUID
            
        Returns:
            True if deleted, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM scan_profiles WHERE profile_id = $1",
                profile_id
            )
            # Result format is "DELETE N" where N is number of rows
            return result.split()[-1] != '0'
    
    async def validate_profile(self, profile_id: UUID) -> bool:
        """
        Validate that a profile exists and is valid.
        
        Args:
            profile_id: Profile UUID
            
        Returns:
            True if valid, False otherwise
        """
        profile = await self.get_profile(profile_id)
        return profile is not None
    
    def _row_to_profile(self, row: asyncpg.Record) -> ScanProfile:
        """
        Convert database row to ScanProfile model.
        
        Args:
            row: Database row
            
        Returns:
            ScanProfile object
        """
        config = row['config'] or {}
        
        return ScanProfile(
            profile_id=row['profile_id'],
            name=row['name'],
            scan_mode=row['scan_mode'],
            config=config,
            created_by=row['created_by'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            # Extract config fields
            max_depth=config.get('max_depth', 5),
            max_pages=config.get('max_pages'),
            max_retries=config.get('max_retries', 3),
            custom_pages=config.get('custom_pages', []),
            accept_button_selector=config.get('accept_button_selector', 'button[data-role="accept"]'),
            wait_for_dynamic_content=config.get('wait_for_dynamic_content', 5),
            follow_external_links=config.get('follow_external_links', False),
            collect_screenshots=config.get('collect_screenshots', False),
            user_agent=config.get('user_agent'),
            viewport=config.get('viewport', {"width": 1366, "height": 768})
        )
