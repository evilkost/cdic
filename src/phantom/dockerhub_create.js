var casper = require('casper').create({
    verbose: true,
    logLevel: "info"
});
casper.options.waitTimeout = 10000; // milliseconds

var repo_name = casper.cli.get("repo_name");
var credentials = casper.cli.get("credentials");

var fs = require('fs');
var utils = require('utils');
var data = JSON.parse(fs.read(credentials));

var username = data.username;
var password = data.password;


casper.start('https://hub.docker.com/account/login/', function() {
    this.fill('form#form-login', {
        'username': username,
        'password': password,
    }, true);
});

casper.thenOpen('https://registry.hub.docker.com/builds/github/select/', function() {
    this.echo(this.getCurrentUrl());
});


casper.thenOpen('https://registry.hub.docker.com/builds/github/' + username + '/' + repo_name, function() {
    this.echo(this.getCurrentUrl());
    this.fill('form#mainform', {}, true);
});

casper.then(function() {
    this.echo(this.getTitle());
    this.debugPage();
});


casper.run();

