/* eslint-disable @typescript-eslint/no-var-requires */
module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [require('@angular-devkit/build-angular/plugins/karma')],
    client: {
      jasmine: {
        random: false,
      },
      clearContext: false,
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/mean-frontend'),
      subdir: '.',
      reporters: [{ type: 'html' }, { type: 'text-summary' }],
    },
    reporters: ['progress'],
    browsers: ['ChromeHeadless'],
    customLaunchers: {
      ChromeHeadless: {
        base: 'Chrome',
        flags: [
          '--headless',
          '--disable-gpu',
          '--no-sandbox',
          '--disable-dev-shm-usage',
          '--remote-debugging-port=9222',
        ],
      },
    },
    restartOnFileChange: true,
  });
};
