import { Component, inject } from '@angular/core';
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';

import { AuthService } from '../core/auth/auth.service';

/**
 * Layout base da área logada (issue #13): navegação conforme a role e logout.
 * Áreas `/aluno` e `/admin` instanciam o mesmo shell e renderizam o conteúdo
 * no `router-outlet` interno.
 */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.css',
})
export class ShellComponent {
  private readonly router = inject(Router);
  readonly auth = inject(AuthService);

  sair(): void {
    this.auth.logout().subscribe(() => {
      void this.router.navigateByUrl('/login');
    });
  }
}
