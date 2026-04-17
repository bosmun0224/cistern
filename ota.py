# ota.py - Over-the-Air updates
import urequests
import os
import machine

try:
    from config import OTA_BASE_URL, OTA_FILES
except ImportError:
    OTA_BASE_URL = None
    OTA_FILES = ['main.py', 'sensor.py', 'ota.py', 'firebase.py', 'provision.py']


def get_local_version():
    """Read local version.txt"""
    try:
        with open('version.txt', 'r') as f:
            return f.read().strip()
    except:
        return "0.0.0"


def get_remote_version():
    """Fetch remote version.txt"""
    if not OTA_BASE_URL:
        return None
    try:
        r = urequests.get(OTA_BASE_URL + "version.txt")
        if r.status_code == 200:
            version = r.text.strip()
            r.close()
            return version
        r.close()
    except Exception as e:
        print(f"Failed to fetch remote version: {e}")
    return None


def download_file(filename):
    """Download a file from OTA server"""
    if not OTA_BASE_URL:
        return False
    
    url = OTA_BASE_URL + filename
    print(f"Downloading {filename}...")
    
    try:
        r = urequests.get(url)
        if r.status_code == 200:
            # Write to temp file first
            temp = filename + '.tmp'
            with open(temp, 'w') as f:
                f.write(r.text)
            r.close()
            
            # Replace original
            try:
                os.remove(filename)
            except:
                pass
            os.rename(temp, filename)
            print(f"  Updated {filename}")
            return True
        r.close()
    except Exception as e:
        print(f"  Failed: {e}")
    return False


def check_for_updates(auto_reboot=True):
    """
    Check for OTA updates and apply if available.
    Returns True if update was applied.
    """
    if not OTA_BASE_URL:
        print("OTA disabled (no OTA_BASE_URL in config)")
        return False
    
    print("Checking for updates...")
    
    local = get_local_version()
    remote = get_remote_version()
    
    print(f"  Local:  {local}")
    print(f"  Remote: {remote}")
    
    if not remote:
        print("Could not fetch remote version")
        return False
    
    if remote == local:
        print("Already up to date")
        return False
    
    # Semantic version comparison: only update if remote > local
    try:
        local_parts = tuple(int(x) for x in local.split('.'))
        remote_parts = tuple(int(x) for x in remote.split('.'))
        if remote_parts <= local_parts:
            print("Already up to date")
            return False
    except (ValueError, AttributeError):
        pass  # Fall through to update if versions aren't parseable
    
    print(f"Update available: {local} -> {remote}")
    
    # Download all OTA files
    success = True
    for filename in OTA_FILES:
        if not download_file(filename):
            success = False
    
    if success:
        # Update version file last
        download_file('version.txt')
        print("Update complete!")
        
        if auto_reboot:
            print("Rebooting...")
            machine.reset()
        return True
    else:
        print("Update failed, keeping current version")
        return False
