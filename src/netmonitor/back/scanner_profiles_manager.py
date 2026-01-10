import re
from pathlib import Path
from typing import Callable, Literal
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pickle

from .scanner_profile import ScannerProfile

SeverityLevel = Literal["information", "warning", "error"]
VALID_NAME_REGEX = r"^[a-zA-Z0-9_-]+$"

class ScannerProfilesManager:
    def __init__(self, profiles_file: str, scheduler: BackgroundScheduler):
        self.profiles_file = Path(profiles_file)
        self.scheduler = scheduler
        self.profiles: list[ScannerProfile] = []

        self.on_message: Callable[[str, str, str], None] | None = None
        self.on_refresh: Callable[[], None] | None = None

        self.load_profiles()

    def _notify(self, msg: str, title: str = "Profile Manager", level: SeverityLevel = "information"):
        if self.on_message:
            self.on_message(msg, title, level)

    def _refresh_front(self):
        if self.on_refresh:
            self.on_refresh()

    def _fail(self, msg: str, level: SeverityLevel = "error", notify: bool = True) -> bool:
        if notify:
            self._notify(msg, level=level)
        return False

    def _ok(self, msg: str | None = None, level: SeverityLevel = "information", notify: bool = True) -> bool:
        if msg and notify:
            self._notify(msg, level=level)
        return True

    def try_save_profiles(self, notify: bool = True) -> bool:
        try:
            self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profiles_file, "wb") as f:
                pickle.dump(self.profiles, f)
            return self._ok("Profiles saved successfully.", notify=notify)
        except Exception as e:
            return self._fail(f"Error saving profiles: {e}", notify=notify)

    def load_profiles(self, notify: bool = True) -> bool:
        if not self.profiles_file.exists():
            if notify:
                self._notify("Profiles file not found. Creating a new one.", level="warning")
            if not self.try_save_profiles(notify=False):
                return self._fail("Failed to create profiles file!", notify=notify)
            return self._ok("New profiles file created.", notify=notify)

        try:
            with open(self.profiles_file, "rb") as f:
                self.profiles = pickle.load(f)
            self._refresh_front()
            return self._ok(f"Loaded {len(self.profiles)} profiles.", notify=notify)
        except Exception as e:
            return self._fail(f"Error loading profiles: {e}", notify=notify)


    def add_profile(self, profile_name: str, notify: bool = True) -> bool:
        if not profile_name:
            return self._fail("Name can't be blank.", "error", notify)
        
        if not re.match(VALID_NAME_REGEX, profile_name):
            return self._fail(f"Bad input '{profile_name}'. Use only letters, numbers, '_' and '-'.", "error", notify)

        if any(p.profile_name == profile_name for p in self.profiles):
            return self._fail(f"Profile {profile_name} already exists.", "warning", notify)

        new_profile = ScannerProfile(profile_name=profile_name)
        self.profiles.append(new_profile)

        if not self.try_save_profiles(notify=False):
            self.profiles.remove(new_profile)
            return self._fail(f"Failed to save profile {profile_name}.", notify=notify)

        self._refresh_front()
        return self._ok(f"Added profile {profile_name}.", notify=notify)

    def delete_profile(self, profile_name: str, notify: bool = True) -> bool:
        before = len(self.profiles)
        self.profiles = [p for p in self.profiles if p.profile_name != profile_name]

        if len(self.profiles) == before:
            return self._fail(f"Profile {profile_name} not found.", "warning", notify)

        if not self.try_save_profiles(notify=False):
            return self._fail(f"Failed to save changes after deleting {profile_name}.", notify=notify)

        self._refresh_front()
        return self._ok(f"Deleted profile {profile_name}.", notify=notify)

    def get_profile(self, profile_name: str) -> ScannerProfile | None:
        return next((p for p in self.profiles if p.profile_name == profile_name), None)

    def update_profile(self, profile_name: str, field: str, value, notify: bool = True) -> bool:
        p = self.get_profile(profile_name)
        if not p:
            return self._fail(f"Profile {profile_name} does not exist.", notify=notify)

        setattr(p, field, value)
        if self.try_save_profiles(notify=False):
            return self._ok(f"Updated profile {profile_name}.", notify=notify)
        else:
            return self._fail(f"Failed to save updated profile {profile_name}.", notify=notify)


    def run_profile_once(self, profile_name: str, notify: bool = True) -> bool:
        p = self.get_profile(profile_name)
        if not p:
            return self._fail(f"Profile {profile_name} not found.", notify=notify)

        try:
            p.scan()
            return self._ok(f"Scan completed for {profile_name}.", notify=notify)
        except Exception as e:
            return self._fail(f"Scan error: {e}", notify=notify)

    def turn_on_profile(self, profile_name: str, notify: bool = True) -> bool:
        p = self.get_profile(profile_name)
        if not p:
            return self._fail(f"Profile {profile_name} not found.", notify=notify)

        try:
            job_id = f"profile_{p.profile_name}"
            self.scheduler.add_job(
                lambda: self.run_profile_once(p.profile_name, notify=False),
                trigger=CronTrigger.from_crontab(p.scheduler),
                id=job_id,
                replace_existing=True
            )
            p.is_active = True
            return self._ok(f"Profile {profile_name} activated.", notify=notify)
        except Exception as e:
            return self._fail(f"Error activating profile: {e}", notify=notify)

    def turn_off_profile(self, profile_name: str, notify: bool = True) -> bool:
        job_id = f"profile_{profile_name}"
        try:
            self.scheduler.remove_job(job_id)
            p = self.get_profile(profile_name)
            if p:
                p.is_active = False
            return self._ok(f"Profile {profile_name} deactivated.", notify=notify)
        except Exception as e:
            return self._fail(f"Error deactivating profile: {e}", notify=notify)

    def set_validated_scheduler(self, profile_name: str, cron_str: str, notify: bool = True) -> bool:
        p = self.get_profile(profile_name)
        if not p:
            return self._fail(f"Profile {profile_name} not found.", notify=notify)

        try:
            CronTrigger.from_crontab(cron_str)
            p.scheduler = cron_str
            if not self.try_save_profiles(notify=False):
                return self._fail(f"Failed to save scheduler for {profile_name}.", notify=notify)
            return self._ok(f"Scheduler updated for {profile_name}.", notify=notify)
        except ValueError as ve:
            return self._fail(f"Invalid CRON: {ve}", notify=notify)
        except Exception as e:
            return self._fail(f"Unexpected error: {e}", notify=notify)

    def get_profile_logs(self, profile_name: str, notify: bool = True):
        p = self.get_profile(profile_name)
        if not p:
            self._fail(f"Profile {profile_name} not found.", "error", notify)
            return None
        return p.get_logs()
