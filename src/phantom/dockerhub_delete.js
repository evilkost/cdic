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

// https://registry.hub.docker.com/u/cdictest/vgologuz-nextgen/delete/

var project_delete_page = "https://registry.hub.docker.com/u/" + username + "/" + repo_name + "/delete/"
casper.thenOpen(project_delete_page, function() {
    //require('utils').dump(x("//*[@name=repository_delete]"));
    this.fill('form[name="repository_delete"]', {}, true)
});


casper.run();

