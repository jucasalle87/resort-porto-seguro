# Dataroom — Resort em Porto Seguro

App em Streamlit com login por usuário/senha, painel master para cadastrar/remover
usuários e log de acessos (quem entrou e em que horário). Mesmo padrão de
autenticação e persistência usado nos outros portais DarkPool (ex.: Fazenda
Barra II).

## 1. Credenciais do master (DarkPool)

- **Usuário:** `darkpool`
- **Senha:** `hRl3OrjdrZwcz8`

Troque essa senha assim que possível pelo menu lateral **"Alterar minha senha"**,
depois de logar.

## 2. Como publicar (GitHub + Streamlit Community Cloud)

1. Crie um repositório novo no GitHub (recomendado: **privado**, já que o
   `config.yaml` guarda e-mails e senhas com hash dos usuários cadastrados).
2. Suba todo o conteúdo desta pasta (`app.py`, `github_storage.py`,
   `requirements.txt`, `config.yaml`, `.streamlit/`, `assets/`, `data/`) para
   esse repositório.
3. Acesse [share.streamlit.io](https://share.streamlit.io), conecte sua conta
   GitHub e clique em "New app".
4. Selecione o repositório, branch `main` e o arquivo `app.py`.
5. **Configure o secret do GitHub** (veja seção 4 abaixo) — sem isso o app
   funciona, mas perde usuários/log a cada restart do container.
6. Deploy. Em alguns minutos o app estará no ar com uma URL tipo
   `https://seu-app.streamlit.app`.
7. Compartilhe essa URL só com quem deve ter acesso — o login protege o
   conteúdo, mas a própria URL não é secreta.

## 3. Cadastrando e removendo usuários

Logado como `darkpool` (master), aparece no menu lateral a opção
**"Administração"**, com duas abas:

- **Usuários** — formulário para cadastrar um novo login (usuário, nome,
  e-mail, senha provisória) e lista de quem tem acesso, com botão para
  remover.
- **Log de Acessos** — tabela com todo login realizado (usuário, nome,
  e-mail, data/hora em horário de Brasília), com botão para baixar em CSV.

Cada usuário cadastrado pode trocar a própria senha pelo menu lateral.

## 4. Persistência via GitHub (resolve o problema de perder dados)

O Streamlit Community Cloud roda o app num container que pode ser reiniciado
do zero (a partir do que está no GitHub) depois de um novo `git push` ou de
um período longo sem uso. Se `config.yaml` (usuários) e `data/access_log.csv`
(log) só existirem no disco desse container, tudo que foi cadastrado depois
do último commit se perde.

Pra resolver isso, o app já vem preparado para sincronizar os dois arquivos
com o próprio repositório GitHub via API (`github_storage.py`) — o mesmo
mecanismo usado no portal da Fazenda Barra II. Com isso configurado, toda vez
que o master cadastra/remove um usuário, ou que alguém faz login, o arquivo
correspondente é atualizado tanto localmente quanto no GitHub — e mesmo que
o container reinicie, o app busca a versão mais recente do GitHub assim que
sobe de novo.

**Como ativar:**

1. Gere um token no GitHub: `Settings da conta > Developer settings >
   Personal access tokens > Fine-grained tokens > Generate new token`.
   Dê acesso só a este repositório, com permissão **Contents: Read and
   write**.
2. No Streamlit Cloud: `Manage app > Settings > Secrets`, cole:

   ```toml
   [github]
   token = "seu-token-aqui"
   repo = "seu-usuario/nome-do-repositorio"
   branch = "main"
   ```

   (Veja `secrets_exemplo.toml` nesta pasta.) Rodando local, o mesmo
   conteúdo vai em `.streamlit/secrets.toml` (esse arquivo não deve ir pro
   GitHub — já está no `.gitignore`).
3. Pronto. Sem esse secret, o app continua funcionando normalmente (fallback
   local), só sem sobreviver a restarts — então vale configurar antes de
   colocar em uso real com investidores.

Cada cadastro de usuário e cada login gera um commit automático no
repositório (ex.: "Registra acesso de 'investidor1'") — é esperado, é assim
que a persistência funciona; não deve gerar tráfego alto o suficiente pra
incomodar (é um dataroom de acesso pontual, não um sistema de alto volume).

## 5. Estrutura de arquivos

```
app.py                  # aplicação Streamlit
github_storage.py        # sincronização de config.yaml/log com o GitHub
requirements.txt        # dependências
config.yaml             # usuários (senhas com hash) + config do cookie de sessão
secrets_exemplo.toml    # modelo do secret do GitHub (não é lido pelo app)
.streamlit/config.toml  # tema visual (cores DarkPool)
assets/                 # fotos do imóvel + logo
data/access_log.csv     # cópia local do log de acessos (espelha o GitHub)
```
