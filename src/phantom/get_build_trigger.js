var casper = require('casper').create({
//    verbose: true,
//    logLevel: "debug",
    viewportSize: {
      width: 1920,
      height: 1080
    }
});
casper.options.waitTimeout = 5000; // milliseconds

// load helpers
var x = require("casper").selectXPath;
var fs = require('fs');
var utils = require('utils');

// load data
var repo_name = casper.cli.get("repo_name");
var credentials = casper.cli.get("credentials");
var save_to = casper.cli.get("save_to");

var data = JSON.parse(fs.read(credentials));

var username = data.username;
var password = data.password;

// scenario start
casper.start('https://hub.docker.com/login/');

var button_create_selector = x("((//form)[2]//input)[3]");
casper.waitForSelector(button_create_selector, function() {
    this.sendKeys(x("((//form)[2]//input)[1]"), username);
    this.sendKeys(x("((//form)[2]//input)[2]"), password);

    this.click(x("((//form)[2]//input)[3]"));
});

var test_after_login_selector = x("//a[text()='Create']");
casper.waitForSelector(test_after_login_selector);

// login done

var builds_conf_url = 'https://hub.docker.com/r/' + username + '/' + repo_name + '/~/settings/automated-builds/';
var activate_selector = x("//button[text()='Activate']");
var deactivate_selector = x("//button[text()='Deactivate']");
var trigger_input_selector = x("(//input[contains(@class, 'Trigger')])[2]");
casper.thenOpen(builds_conf_url, function(){
    casper.wait(3000);
    casper.click(activate_selector)
});

casper.waitForSelector(deactivate_selector, function(){
    casper.wait(3000);
    var trigger_url = casper.getElementInfo(trigger_input_selector).attributes["value"];
    var result = {
        "repo_name": repo_name,
        "trigger_url": trigger_url
    };

    //    casper.echo("saving to: " + save_to);
    fs.write(save_to, JSON.stringify(result), 'w');
});

casper.run();

