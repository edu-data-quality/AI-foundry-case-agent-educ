import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';

import { authInterceptor } from './core/auth/auth.interceptor';
import { routes } from './app.routes';
import { MockSessaoAlunoService } from './services/mock-sessao-aluno.service';
import { SessaoAlunoService } from './services/sessao-aluno.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    // MOCK do #15: trocar pela sessão real do #13 (token JWT/cpf do login) no merge.
    { provide: SessaoAlunoService, useClass: MockSessaoAlunoService },
  ],
};