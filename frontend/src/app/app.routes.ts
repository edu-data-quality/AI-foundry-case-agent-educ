import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { Role } from './core/auth/role';
import { roleGuard } from './core/auth/role.guard';
import { LoginComponent } from './login/login.component';
import { AdminAlunosComponent } from './pages/admin-alunos/admin-alunos.component';
import { AdminPainelComponent } from './pages/admin-painel/admin-painel.component';
import { AlunoChatComponent } from './pages/aluno-chat/aluno-chat.component';
import { DashboardAlunoComponent } from './pages/dashboard-aluno/dashboard-aluno.component';
import { ShellComponent } from './shell/shell.component';

/**
 * Rotas do portal (issues #13 + #15): login aberto; áreas `/aluno` e `/admin`
 * protegidas por `authGuard` (sessão) + `roleGuard` (role correta), com o
 * shell como layout compartilhado. O dashboard acadêmico (#15) vive em
 * `/aluno/dashboard`; a listagem de alunos do ADMIN (#16) em `/admin/alunos`.
 */
export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
    title: 'Entrar | Assistente Académico EAD',
  },
  {
    path: 'aluno',
    component: ShellComponent,
    canActivate: [authGuard, roleGuard(Role.ALUNO)],
    children: [
      {
        path: '',
        pathMatch: 'full',
        component: AlunoChatComponent,
        title: 'Chat | Área do Aluno',
      },
      {
        path: 'dashboard',
        component: DashboardAlunoComponent,
        title: 'Dashboard Académico | Área do Aluno',
      },
    ],
  },
  {
    path: 'admin',
    component: ShellComponent,
    canActivate: [authGuard, roleGuard(Role.ADMIN)],
    children: [
      {
        path: '',
        pathMatch: 'full',
        component: AdminPainelComponent,
        title: 'Painel | Administração',
      },
      {
        path: 'alunos',
        component: AdminAlunosComponent,
        title: 'Alunos | Administração',
      },
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];