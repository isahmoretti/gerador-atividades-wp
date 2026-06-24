import base64
import os
import streamlit as st
from urllib.parse import quote
import requests
from openai import OpenAI

CSS = """.atividade-pdf-wrap{margin:20px 0 28px}
.atividade-pdf-btn{display:flex!important;align-items:center;justify-content:center;gap:10px;width:100%;padding:16px 20px;border:0;border-radius:6px;cursor:pointer;font-size:17px;font-weight:700;color:#fff!important;background:#2E7D32;text-decoration:none!important;letter-spacing:1px;text-transform:uppercase;box-shadow:0 3px 8px rgba(0,0,0,.22);transition:background .2s}
.atividade-pdf-btn:hover{background:#1B5E20;color:#fff!important;text-decoration:none!important}
.atividade-pdf-btn svg{flex-shrink:0}"""

LIMITE_CHARS = 122


def contar_chars(texto):
    return len(texto.strip())


def gerar_bloco(imgs_urls):
    imgs_validas = [u.strip() for u in imgs_urls if u.strip()]
    imgs_param = ",".join(imgs_validas)
    pdf_url = "/pdf/pdf.php?imgs=" + quote(imgs_param, safe="")

    return (
        '<div class="atividade-pdf-wrap">\n'
        f'  <a href="{pdf_url}" target="_blank" class="atividade-pdf-btn"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="white"><path d="M5 20h14v-2H5v2zm7-18L5.33 9h4.34v4h4.66V9h4.34L12 2z"/></svg> BAIXAR EXERC&#205;CIO EM PDF</a>\n'
        '</div>'
    )


def caixa_codigo(label, codigo, lang):
    st.markdown(f"**{label}**")
    st.code(codigo, language=lang)


def gerar_alt_text_ia(url, api_key):
    try:
        from urllib.parse import urlparse
        origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": origin,
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        })
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if content_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            if url.lower().endswith(".webp"):
                content_type = "image/webp"
            elif url.lower().endswith(".png"):
                content_type = "image/png"
            elif url.lower().endswith(".gif"):
                content_type = "image/gif"
            else:
                content_type = "image/jpeg"

        b64 = base64.b64encode(resp.content).decode("utf-8")
        data_url = f"data:{content_type};base64,{b64}"

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Gere um alt text otimizado para SEO desta imagem em português brasileiro. "
                                "O alt text deve:\n"
                                "- Descrever fielmente o conteúdo da imagem\n"
                                "- Incluir palavras-chave relevantes de forma natural\n"
                                "- Ter no máximo 122 caracteres (não palavras, caracteres)\n"
                                "- Ser útil para pessoas com deficiência visual\n"
                                "- Não começar com 'Imagem de', 'Foto de' ou similar\n"
                                "Responda somente com o alt text, sem nenhuma explicação adicional."
                            ),
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content.strip()
    except requests.exceptions.RequestException as e:
        return f"Erro ao baixar imagem: {e}"
    except Exception as e:
        return f"Erro: {e}"


def main():
    st.set_page_config(
        page_title="Gerador de Atividades para WordPress",
        page_icon="📝",
        layout="wide",
    )

    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    with st.sidebar:
        st.header("Configuração")
        if api_key:
            st.success("Chave da API detectada via variável de ambiente.")
        else:
            api_key = st.text_input(
                "Chave da API OpenAI",
                type="password",
                help="Necessária para gerar alt text automaticamente com IA",
            )
        st.caption("A chave é usada apenas localmente para chamadas à API.")

    st.title("Gerador de Atividades para WordPress")
    st.markdown(
        "Preencha as URLs das imagens de cada atividade e clique em **Gerar códigos**. "
        "Cole o bloco gerado na aba HTML do bloco Gutenberg."
    )

    st.divider()

    if "num_atividades" not in st.session_state:
        st.session_state.num_atividades = 1

    col_add, col_rem, _ = st.columns([1.2, 1.4, 5])
    with col_add:
        if st.button("+ Adicionar atividade", use_container_width=True):
            st.session_state.num_atividades += 1
            st.rerun()
    with col_rem:
        if st.button("- Remover última", use_container_width=True):
            if st.session_state.num_atividades > 1:
                st.session_state.num_atividades -= 1
                st.rerun()

    st.divider()

    imgs_list = []
    alts_list = []

    for i in range(st.session_state.num_atividades):
        st.subheader(f"Atividade {i + 1}")

        col_imgs, col_alts = st.columns(2)

        with col_imgs:
            imgs_raw = st.text_area(
                "URLs das imagens (uma por linha)",
                key=f"img_{i}",
                height=120,
                placeholder="https://viacarreira.com/wp-content/uploads/folha1.webp\nhttps://viacarreira.com/wp-content/uploads/folha2.webp",
            )

        urls = [u.strip() for u in imgs_raw.splitlines() if u.strip()]
        imgs_list.append(urls)

        alts_atividade = []
        with col_alts:
            if urls:
                for j, url in enumerate(urls):
                    nome = url.rstrip("/").split("/")[-1]

                    # Transfere valor gerado pela IA para o widget antes de criá-lo
                    staging_key = f"alt_gen_{i}_{j}"
                    widget_key = f"alt_{i}_{j}"
                    if staging_key in st.session_state:
                        st.session_state[widget_key] = st.session_state.pop(staging_key)

                    alt = st.text_area(
                        f"Alt text — imagem {j + 1} ({nome})",
                        key=widget_key,
                        height=80,
                        placeholder="Ex: Atividade de alfabetização com sílabas para imprimir — 1º ano",
                    )

                    btn_col, count_col = st.columns([2, 3])
                    with btn_col:
                        if st.button(
                            "Gerar com IA",
                            key=f"btn_ia_{i}_{j}",
                            use_container_width=True,
                        ):
                            if api_key:
                                with st.spinner("Analisando imagem..."):
                                    resultado = gerar_alt_text_ia(url, api_key)
                                    st.session_state[staging_key] = resultado
                                st.rerun()
                            else:
                                st.warning("Adicione a chave da API na barra lateral.")

                    with count_col:
                        chars = contar_chars(alt)
                        if chars > LIMITE_CHARS:
                            st.error(f"{chars}/{LIMITE_CHARS} caracteres — reduzir")
                        elif chars > 0:
                            st.success(f"{chars}/{LIMITE_CHARS} caracteres")
                        else:
                            st.caption(f"0/{LIMITE_CHARS} caracteres")

                    alts_atividade.append(alt.strip())
            else:
                st.info("Preencha as URLs das imagens ao lado para liberar os campos de alt text.")

        alts_list.append(alts_atividade)

        if i < st.session_state.num_atividades - 1:
            st.divider()

    st.divider()

    if st.button("Gerar códigos", type="primary"):
        st.subheader("CSS — cole uma vez em Aparência → Personalizar → CSS adicional")
        caixa_codigo("CSS", CSS, "css")

        st.divider()
        st.subheader("Blocos HTML por atividade")
        st.caption("Cole na aba HTML de cada bloco Gutenberg.")

        for i in range(st.session_state.num_atividades):
            with st.expander(f"Atividade {i + 1}", expanded=True):
                caixa_codigo("HTML", gerar_bloco(imgs_list[i]), "html")

        tem_alts = any(any(a for a in alts) for alts in alts_list)
        if tem_alts:
            st.divider()
            st.subheader("Alt texts para a Biblioteca de Mídia")
            st.caption("Copie o alt text de cada imagem ao fazer upload no WordPress.")

            for i, (urls, alts) in enumerate(zip(imgs_list, alts_list)):
                if not urls:
                    continue
                st.markdown(f"**Atividade {i + 1}**")
                for j, (url, alt) in enumerate(zip(urls, alts)):
                    nome = url.rstrip("/").split("/")[-1]
                    chars = contar_chars(alt)
                    st.markdown(f"**Imagem {j + 1}** — `{nome}`")
                    if alt:
                        st.code(alt, language=None)
                        cor = "red" if chars > LIMITE_CHARS else "green"
                        st.markdown(f":{cor}[{chars}/{LIMITE_CHARS} caracteres]")
                    else:
                        st.warning("Alt text não preenchido.")


if __name__ == "__main__":
    main()
