"""Non-blocking, rate-limited bilingual voice alert engine with recurring score announcements.

Supports English ('en') and Tamil ('ta') with offline-only text-to-speech synthesis
(pyttsx3 SAPI5 for English and eSpeak-NG for Tamil).
Executes audio synthesis and periodic score announcements in background worker threads
to ensure the video capture and AI inference loops are never stalled, while guaranteeing
score announcements never overlap or interrupt active violation alerts.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

import pyttsx3

from src.alerts.phrases import (
    BILINGUAL_ALERT_PHRASES,
    format_score_announcement,
    get_alert_phrase,
    normalize_language,
)
from src.config import ALERTS

# Standard alert phrases for backward compatibility
STANDARD_ALERT_PHRASES: Dict[str, str] = {
    k: v["en"] for k, v in BILINGUAL_ALERT_PHRASES.items()
}

DEFAULT_ANNOUNCEMENT_INTERVAL_SECONDS: float = getattr(ALERTS, "SCORE_ANNOUNCEMENT_INTERVAL_SECONDS", 600.0)


def find_espeak_executable() -> Optional[str]:
    """Search for offline eSpeak-NG or eSpeak executable on PATH and common install locations."""
    # 1. Check system PATH
    for candidate in ["espeak-ng", "espeak", "espeak-ng.exe", "espeak.exe"]:
        found = shutil.which(candidate)
        if found:
            return found

    # 2. Check standard Windows Program Files directories
    standard_paths = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "eSpeak NG" / "espeak-ng.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "eSpeak NG" / "espeak-ng.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "eSpeak" / "command_line" / "espeak.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "eSpeak" / "command_line" / "espeak.exe",
    ]
    for p in standard_paths:
        if p.exists():
            return str(p)

    return None


def play_alarm_tone(event_type: str) -> None:
    """Play hardware alarm beep/chime tone on Windows for safety violations."""
    try:
        import winsound
        evt = str(event_type).strip().lower()
        if evt in ("drowsiness", "drowsy"):
            # Urgent high-pitch double alarm for drowsiness / microsleep
            winsound.Beep(1500, 140)
            time.sleep(0.04)
            winsound.Beep(1900, 180)
        elif evt in ("phone", "mobile_phone"):
            # Double alert tone for mobile phone
            winsound.Beep(1300, 110)
            time.sleep(0.04)
            winsound.Beep(1300, 110)
        elif evt in ("distraction", "distracted", "smoking", "drinking"):
            # Alert warning tone
            winsound.Beep(1200, 160)
        elif evt in ("seatbelt", "no_seatbelt"):
            # Seatbelt chime
            winsound.Beep(1000, 180)
    except Exception:
        pass


class AlertManager:
    """Non-blocking, queue-based bilingual Voice Alert Manager with per-event rate limiting

    and periodic recurring score announcements.
    """

    def __init__(
        self,
        rate_limit_seconds: float = ALERTS.RATE_LIMIT_SECONDS,
        speech_rate: int = ALERTS.SPEECH_RATE,
        volume: float = ALERTS.VOLUME,
        enable_audio: bool = True,
        announcement_interval: float = DEFAULT_ANNOUNCEMENT_INTERVAL_SECONDS,
    ) -> None:
        """Initialize AlertManager.

        Args:
            rate_limit_seconds: Minimum seconds between repeated alerts of same type (default: 8.0s).
            speech_rate: Words per minute speech rate (default: 175).
            volume: Audio volume [0.0, 1.0] (default: 1.0).
            enable_audio: Flag to enable or mute physical TTS speech playback.
            announcement_interval: Default interval in seconds between recurring score announcements (default: 600.0s).
        """
        self.rate_limit_seconds = rate_limit_seconds
        self.speech_rate = speech_rate
        self.volume = volume
        self.enable_audio = enable_audio
        self.announcement_interval = announcement_interval

        # Rate limiting state: event_type -> last_triggered_timestamp
        self._last_played_times: Dict[str, float] = {}
        self._lock = threading.Lock()

        # Non-blocking speech queue & worker thread: holds (phrase, event_type, language)
        self._speech_queue: queue.Queue = queue.Queue(maxsize=30)
        self._stop_event = threading.Event()

        # Offline TTS backend discovery
        self.espeak_bin = find_espeak_executable()

        # Track spoken items for verification/telemetry
        self.spoken_history: List[Dict[str, Any]] = []
        self._is_speaking = False

        self._worker_thread = threading.Thread(
            target=self._speech_worker,
            name="VoiceAlertWorker",
            daemon=True,
        )
        self._worker_thread.start()

        # Score announcement timer thread state
        self._announcement_thread: Optional[threading.Thread] = None
        self._announcement_stop_event = threading.Event()
        self._announcement_count: int = 0

    @property
    def is_speaking(self) -> bool:
        """Return whether audio synthesizer is currently actively speaking."""
        return self._is_speaking

    @property
    def announcement_count(self) -> int:
        """Return total count of score announcements queued during session."""
        return self._announcement_count

    @property
    def is_announcement_running(self) -> bool:
        """Return whether the background announcement timer is actively running."""
        return self._announcement_thread is not None and self._announcement_thread.is_alive()

    def _speech_worker(self) -> None:
        """Background thread worker loop consuming speech requests from queue sequentially."""
        # Initialize COM on Windows for SAPI5 thread safety
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        pyttsx_engine: Optional[pyttsx3.Engine] = None
        try:
            pyttsx_engine = pyttsx3.init()
            pyttsx_engine.setProperty("rate", self.speech_rate)
            pyttsx_engine.setProperty("volume", self.volume)
        except Exception as e:
            print(f"[!] Warning: Could not initialize pyttsx3 TTS engine: {e}")

        while not self._stop_event.is_set():
            try:
                # Wait for next alert item with timeout for responsive shutdown
                item = self._speech_queue.get(timeout=0.1)
                if item is None:
                    # Sentinel value to exit worker
                    self._speech_queue.task_done()
                    break

                phrase, event_type, language = item
                self._is_speaking = True

                # Record spoken log
                record = {
                    "phrase": phrase,
                    "event_type": event_type,
                    "language": language,
                    "timestamp": time.time(),
                }
                self.spoken_history.append(record)

                if self.enable_audio:
                    self._play_offline_speech(phrase, event_type, language, pyttsx_engine)

                self._is_speaking = False
                self._speech_queue.task_done()

            except queue.Empty:
                self._is_speaking = False
                continue
            except Exception:
                self._is_speaking = False
                continue

        # Clean up pyttsx3 engine on worker exit
        if pyttsx_engine is not None:
            try:
                pyttsx_engine.stop()
            except Exception:
                pass

    def _play_offline_speech(
        self,
        phrase: str,
        event_type: str,
        language: str,
        pyttsx_engine: Optional[pyttsx3.Engine],
    ) -> None:
        """Play offline speech using eSpeak-NG (for Tamil) or pyttsx3 SAPI5 (for English)."""
        lang = normalize_language(language)

        # Trigger hardware alarm tone for safety violations
        if event_type in ("drowsiness", "distraction", "phone", "smoking", "drinking", "seatbelt"):
            play_alarm_tone(event_type)

        if lang == "ta":
            # 1. Try eSpeak-NG with native offline Tamil voice model (-v ta)
            if self.espeak_bin:
                try:
                    subprocess.run(
                        [self.espeak_bin, "-v", "ta", "-s", str(int(self.speech_rate * 0.9)), phrase],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5.0,
                        check=False,
                    )
                    return
                except Exception as e:
                    print(f"[!] eSpeak-NG playback error for '{event_type}': {e}")

            # 2. Offline fallback if eSpeak-NG is not installed on the system
            # Print console notification keeping zero-cloud promise
            try:
                print(f"[*] [AUDIO ALERT - TAMIL] {phrase}")
            except UnicodeEncodeError:
                safe_phrase = phrase.encode("ascii", errors="backslashreplace").decode("ascii")
                print(f"[*] [AUDIO ALERT - TAMIL] {safe_phrase}")

            if pyttsx_engine is not None:
                try:
                    pyttsx_engine.say(phrase)
                    pyttsx_engine.runAndWait()
                except Exception:
                    pass
        else:
            # English standard speech via pyttsx3 SAPI5
            if pyttsx_engine is not None:
                try:
                    pyttsx_engine.say(phrase)
                    pyttsx_engine.runAndWait()
                except Exception as e:
                    print(f"[!] pyttsx3 playback error for '{event_type}': {e}")

    def is_rate_limited(self, event_type: str, current_time: Optional[float] = None) -> bool:
        """Check if an event type is currently in its cooldown window."""
        now = current_time if current_time is not None else time.time()
        with self._lock:
            last_time = self._last_played_times.get(event_type.strip().lower())
            if last_time is None:
                return False
            return (now - last_time) < self.rate_limit_seconds

    def get_remaining_cooldown(self, event_type: str, current_time: Optional[float] = None) -> float:
        """Return remaining seconds of cooldown for given event type (0.0 if ready)."""
        now = current_time if current_time is not None else time.time()
        with self._lock:
            last_time = self._last_played_times.get(event_type.strip().lower())
            if last_time is None:
                return 0.0
            elapsed = now - last_time
            return max(0.0, self.rate_limit_seconds - elapsed)

    def trigger(self, event_type: str, language: str = "en", force: bool = False) -> bool:
        """Trigger a bilingual voice alert for the specified event type.

        Non-blocking: returns immediately after enqueuing.

        Args:
            event_type: One of 'drowsiness', 'distraction', 'phone', 'seatbelt', 'smoking', 'drinking', 'recovery'.
            language: Target language ('en' for English, 'ta' for Tamil).
            force: If True, bypasses rate-limiting.

        Returns:
            True if alert was queued, False if skipped due to rate limiting.
        """
        clean_event = event_type.strip().lower()
        lang = normalize_language(language)
        phrase = get_alert_phrase(clean_event, language=lang)

        now = time.time()
        with self._lock:
            if not force and clean_event in self._last_played_times:
                elapsed = now - self._last_played_times[clean_event]
                if elapsed < self.rate_limit_seconds:
                    # Rate limited - skip to avoid spamming driver
                    return False

            self._last_played_times[clean_event] = now

        try:
            # Enqueue without blocking the video capture / AI inference loop
            self._speech_queue.put_nowait((phrase, clean_event, lang))
            return True
        except queue.Full:
            print(f"[!] Warning: Voice alert queue is full. Dropping alert: {clean_event}")
            return False

    def trigger_phrase(self, custom_phrase: str, language: str = "en", force: bool = False) -> bool:
        """Play a custom spoken message (non-blocking)."""
        lang = normalize_language(language)
        try:
            self._speech_queue.put_nowait((custom_phrase, "custom", lang))
            return True
        except queue.Full:
            return False

    def start_score_announcements(
        self,
        score_callback: Callable[[], Tuple[int, str]],
        language: str = "en",
        interval: Optional[float] = None,
    ) -> None:
        """Start the background recurring score announcement timer for an active session.

        Args:
            score_callback: Callable returning (current_score: int, risk_level: str).
            language: Language preference ('en' or 'ta').
            interval: Optional custom interval in seconds (defaults to self.announcement_interval / 600s).
        """
        # Stop any existing running announcement timer
        self.stop_score_announcements()

        target_interval = interval if interval is not None else self.announcement_interval
        self._announcement_stop_event.clear()

        def _announcement_loop() -> None:
            while not self._announcement_stop_event.is_set():
                # Non-busy wait using Event.wait()
                interrupted = self._announcement_stop_event.wait(timeout=target_interval)
                if interrupted or self._announcement_stop_event.is_set() or self._stop_event.is_set():
                    break

                try:
                    score, risk_level = score_callback()
                    phrase = format_score_announcement(score=score, risk_level=risk_level, language=language)
                    # Enqueue without blocking or interrupting active alerts
                    self._speech_queue.put_nowait((phrase, "score_announcement", language))
                    self._announcement_count += 1
                except Exception as e:
                    print(f"[!] Warning: Score announcement error: {e}")

        self._announcement_thread = threading.Thread(
            target=_announcement_loop,
            name="ScoreAnnouncementTimer",
            daemon=True,
        )
        self._announcement_thread.start()

    def stop_score_announcements(self) -> None:
        """Stop the recurring score announcement timer cleanly."""
        self._announcement_stop_event.set()
        if self._announcement_thread is not None and self._announcement_thread.is_alive():
            self._announcement_thread.join(timeout=1.0)
        self._announcement_thread = None

    def wait_until_done(self, timeout: Optional[float] = None) -> None:
        """Wait until all currently queued speech tasks are finished playing."""
        try:
            self._speech_queue.join()
        except Exception:
            pass

    def stop(self) -> None:
        """Shut down the background speech worker and announcement timer cleanly."""
        self.stop_score_announcements()
        self._stop_event.set()
        try:
            self._speech_queue.put_nowait(None)
        except Exception:
            pass
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def __enter__(self) -> "AlertManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


# Default singleton instance for convenience
_default_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create singleton AlertManager instance."""
    global _default_alert_manager
    if _default_alert_manager is None:
        _default_alert_manager = AlertManager()
    return _default_alert_manager


def trigger_alert(event_type: str, language: str = "en", force: bool = False) -> bool:
    """Convenience function to trigger a voice alert on the default AlertManager."""
    return get_alert_manager().trigger(event_type, language=language, force=force)
