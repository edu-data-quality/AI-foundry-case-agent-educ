import { TestBed } from '@angular/core/testing';
import { AdminPainelComponent } from './admin-painel.component';

describe('AdminPainelComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminPainelComponent],
    }).compileComponents();
  });

  it('deve criar a página do painel admin', () => {
    const fixture = TestBed.createComponent(AdminPainelComponent);
    expect(fixture.componentInstance).toBeTruthy();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Painel do Administrador');
  });
});
