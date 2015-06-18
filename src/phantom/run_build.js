var casper = require('casper').create({
    verbose: true,
    logLevel: "info"
});
var x = require("casper").selectXPath;

casper.options.waitTimeout = 10000; // milliseconds

var repo_name = casper.cli.get("repo_name");
var credentials = casper.cli.get("credentials");

var fs = require('fs');
var utils = require('utils');
var data = JSON.parse(fs.read(credentials));

var username = data.username;
var password = data.password;
var github_username = data.github_username;


casper.start('https://hub.docker.com/account/login/', function() {
    this.fill('form#form-login', {
        'username': username,
        'password': password,
    }, true);
});

var project_page = "https://registry.hub.docker.com/u/" + username + "/" + repo_name + "/"
casper.thenOpen(project_page, function() {
    this.click(x("//*[contains(text(),'xStart a Build')]"));
});


casper.run();

