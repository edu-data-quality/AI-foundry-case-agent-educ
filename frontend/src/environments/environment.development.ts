/**
 * Configurações do ambiente de desenvolvimento (`ng serve`/`ng build -c development`).
 *
 * O `angular.json` substitui `environment.ts` por este arquivo na configuração
 * `development`. Por isso os valores são declarados aqui diretamente: um
 * `export { environment }` de `./environment` viraria auto-importação circular
 * depois da substituição (erro TS2303).
 */
export const environment = {
  apiUrl: 'http://localhost:8000',
};
