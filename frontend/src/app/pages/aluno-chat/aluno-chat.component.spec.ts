import { TestBed } from '@angular/core/testing';
import { AlunoChatComponent } from './aluno-chat.component';

describe('AlunoChatComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlunoChatComponent],
    }).compileComponents();
  });

  it('deve criar a página da área do aluno', () => {
    const fixture = TestBed.createComponent(AlunoChatComponent);
    expect(fixture.componentInstance).toBeTruthy();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Chat do Aluno');
  });
});
