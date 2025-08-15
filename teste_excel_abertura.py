import pythoncom
import win32com.client as win32
import os

CAMINHO = r"C:\Polymusic Royalties\uploads\sps\SP_BARTO_GALENO.xlsx"

pythoncom.CoInitialize()

try:
    print(f"[TESTE] Tentando abrir: {CAMINHO}")
    if not os.path.exists(CAMINHO):
        print("❌ Arquivo não encontrado.")
    else:
        excel = win32.gencache.EnsureDispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3

        wb = excel.Workbooks.Open(os.path.abspath(CAMINHO))
        print("✅ Arquivo aberto com sucesso via COM.")
        wb.Close(False)
        excel.Quit()

except Exception as e:
    import traceback
    print("[ERRO] Falha ao abrir via COM:")
    traceback.print_exc()

finally:
    pythoncom.CoUninitialize()
