/**
 * Configurações por ambiente do frontend.
 *
 * `apiUrl` é a base da API FastAPI (sem barra final). O backend expõe os
 * endpoints sob `/api/*` (ex: `POST /api/auth/login`), então os services
 * concatenam os paths diretamente.
 */
export const environment = {
  apiUrl: 'http://localhost:8000',
};
