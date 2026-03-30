' Windows Arka Plan Çalıştırıcısı (Görünmez Mod)
' Ekranda sürekli açık kalan CMD penceresi yerine sessizce çalışır.
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "start_bot.bat" & Chr(34), 0
Set WshShell = Nothing
