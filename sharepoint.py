"""
Dependências necessárias:
    pip install pandas Office365-REST-Python-Client openpyxl

Como usar:
    df = read_sharepoint_excel_to_df(
        sharepoint_url="<URL do arquivo>",
        username="<seu email>",
        password="<sua senha>"
    )
"""
import io
import pandas as pd
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from urllib.parse import urlparse
import requests
from io import BytesIO, StringIO

# --- Configuração do arquivo e credenciais ---
SHAREPOINT_URL = "https://premiumgrpinc78.sharepoint.com/sites/PremiumHVAC593/_layouts/15/doc.aspx?sourcedoc={75cc06d4-9703-4d88-aa79-258015241355}&action=edit"
USERNAME = "vitor@premiumgrpinc.com"
PASSWORD = "Pantheon@8278"

# Link público do SharePoint fornecido
SHAREPOINT_PUBLIC_URL = "https://premiumgrpinc78.sharepoint.com/sites/premium/_layouts/15/download.aspx?UniqueId=818c69b2%2D86fd%2D4c1b%2D8e39%2D6c2f52daf837"

# O caminho do arquivo no SharePoint precisa ser ajustado manualmente!
# Exemplo: /sites/PremiumHVAC593/Shared Documents/NOME_DA_PASTA/NOME_DO_ARQUIVO.xlsx
# Tentei inferir, mas se der erro, ajuste manualmente o file_url abaixo.
def get_file_url():
    # Tente inferir o caminho do arquivo
    # Se não funcionar, ajuste manualmente
    return "/sites/PremiumHVAC593/Shared Documents/Timesheet.xlsx"  # <-- AJUSTE AQUI se necessário


def read_sharepoint_excel_to_df(sharepoint_url: str, username: str, password: str, sheet_name=0, **kwargs) -> pd.DataFrame:
    """
    Faz download de uma planilha Excel do SharePoint Online e retorna um DataFrame pandas.
    sharepoint_url: URL do arquivo no SharePoint (link de compartilhamento ou direto)
    username: Usuário do Microsoft 365
    password: Senha do Microsoft 365
    sheet_name: Nome ou índice da aba do Excel (padrão: 0)
    kwargs: argumentos adicionais para pandas.read_excel
    """
    # Extrair site e caminho do arquivo
    # Exemplo de URL:
    # https://premiumgrpinc78.sharepoint.com/sites/PremiumHVAC593/_layouts/15/doc.aspx?sourcedoc={75cc06d4-9703-4d88-aa79-258015241355}&action=edit
    # O caminho real do arquivo é geralmente /sites/<site>/Shared Documents/<pasta>/<arquivo>
    # Você pode obter o caminho correto pelo link de "copiar link" no SharePoint (deve terminar com .xlsx)

    # Exemplo de extração do caminho do arquivo
    parsed = urlparse(sharepoint_url)
    site_url = f"{parsed.scheme}://{parsed.netloc}/sites/PremiumHVAC593"
    file_url = get_file_url()
    print(f"Conectando ao site: {site_url}")
    print(f"Caminho do arquivo: {file_url}")
    ctx = ClientContext(site_url).with_credentials(UserCredential(username, password))
    buffer = io.BytesIO()
    file = ctx.web.get_file_by_server_relative_url(file_url)
    file.download(buffer).execute_query()
    buffer.seek(0)
    print("Arquivo baixado, lendo com pandas...")
    df = pd.read_excel(buffer, sheet_name=sheet_name, **kwargs)
    return df


SHAREPOINT_CSV_URL = "https://usc-excel.officeapps.live.com/x/_layouts/XlFileHandler.aspx?sheetName=Permits&downloadAsCsvEnabled=1&WacUserType=WOPI&usid=03337c63-342b-5c32-4ade-2938d794cb43&NoAuth=1&waccluster=GCL1"

if __name__ == "__main__":
    try:
        response = requests.get(SHAREPOINT_CSV_URL)
        response.raise_for_status()
        try:
            df = pd.read_csv(StringIO(response.text))
            print(df.head())
        except Exception as e:
            print(f"Erro ao ler CSV: {e}")
            print("Conteúdo baixado (início):")
            print(response.text[:200])
    except Exception as e:
        print(f"Erro ao baixar arquivo: {e}")
