// Configuração extra do Karma (mergeada pelo builder do Angular com a
// config gerada). O Chrome disponível neste ambiente é o do Windows (WSL
// interop): roda headless com perfil temporário em caminho Windows.
module.exports = function (config) {
  config.set({
    browsers: ['ChromeHeadlessNoSandbox'],
    customLaunchers: {
      ChromeHeadlessNoSandbox: {
        base: 'ChromeHeadless',
        flags: [
          '--headless=new',
          '--no-sandbox',
          '--disable-gpu',
          '--disable-dev-shm-usage',
          '--remote-debugging-port=9222',
          '--user-data-dir=C:\\Users\\eduardopf\\AppData\\Local\\Temp\\karma-chrome',
        ],
      },
    },
    captureTimeout: 120000,
    browserNoActivityTimeout: 120000,
  });
};
