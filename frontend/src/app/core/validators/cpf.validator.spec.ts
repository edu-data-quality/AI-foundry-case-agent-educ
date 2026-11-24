import { FormControl } from '@angular/forms';

import { cpfValido, cpfValidator } from './cpf.validator';

describe('cpfValido', () => {
  it('aceita CPF com dígitos verificadores corretos, com ou sem máscara', () => {
    expect(cpfValido('52998224725')).toBeTrue();
    expect(cpfValido('529.982.247-25')).toBeTrue();
  });

  it('rejeita CPF com dígito verificador errado', () => {
    expect(cpfValido('52998224724')).toBeFalse();
  });

  it('rejeita quantidade diferente de 11 dígitos', () => {
    expect(cpfValido('123')).toBeFalse();
    expect(cpfValido('529982247250')).toBeFalse();
  });

  it('rejeita sequências repetidas', () => {
    expect(cpfValido('00000000000')).toBeFalse();
    expect(cpfValido('11111111111')).toBeFalse();
  });
});

describe('cpfValidator', () => {
  it('devolve erro cpfInvalido para CPF inválido', () => {
    const controle = new FormControl('111.111.111-11');
    expect(cpfValidator(controle)).toEqual({ cpfInvalido: true });
  });

  it('devolve null para CPF válido', () => {
    const controle = new FormControl('529.982.247-25');
    expect(cpfValidator(controle)).toBeNull();
  });

  it('não valida campo vazio (required cuida disso)', () => {
    const controle = new FormControl('');
    expect(cpfValidator(controle)).toBeNull();
  });
});
