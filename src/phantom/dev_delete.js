var casper = require('casper').create({
    verbose: true,
    logLevel: "debug",
    pageSettings: {
        userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11"
    },
    viewportSize: {
      width: 1920,
      height: 1080
    }
});
var x = require("casper").selectXPath;
var utils = require('utils');

// var repo_name = casper.cli.get("repo_name");
// var credentials = casper.cli.get("credentials");

// var data = JSON.parse(fs.read(credentials));

var username = "fedorainfratesting";
var password = "";
//var repo_name = "dh1";
var repo_name = "vgologuz-test2";

// var username = data.username;
// var password = data.password;
var github_username = "FedoraInfraTesting";

var GITHUB_USER = 'FedoraInfraTesting';
var GITHUB_API_ROOT = 'https://api.github.com';

//
//casper.options.onResourceRequested = function(C, requestData, request) {
//    // casper.on('page.resource.requested', function(requestData, request) {
//    this.echo("== On request" + requestData.url);
//    utils.dump(requestData.postData);
//
//};
//casper.options.onResourceReceived = function(C, response) {
//    this.echo("== On response  "  + response.url + " status " + response.status);
//    utils.dump(response.body);
//
//};


casper.on("page.error", function(msg, trace) {
    this.echo("Error: " + msg, "ERROR");
});

casper.options.waitTimeout = 10000; // milliseconds

var login_done = false;


casper.start('https://hub.docker.com/login/', function() {
    this.capture("000-login_page.png");
});

var button_create_selector = x("((//form)[2]//input)[3]");
casper.waitForSelector(button_create_selector, function() {
    this.sendKeys(x("((//form)[2]//input)[1]"), username);
    this.sendKeys(x("((//form)[2]//input)[2]"), password);

    this.click(x("((//form)[2]//input)[3]"));
});

var test_after_login_selector = x("//input[@placeholder='Type to filter repositories by name']");
casper.waitForSelector(test_after_login_selector, function() {
    this.echo(this.getCurrentUrl());
    this.capture("001-login_should_be_done.png");
});

var dh_repo_url_delete = 'https://hub.docker.com/r/' +username + '/' + repo_name + '/~/settings/'

casper.thenOpen(dh_repo_url_delete);

var delete_button_selector = x("(//button)[text()='Delete']");
var delete_input_selector = x("(//input)[2]");
casper.waitForSelector(delete_button_selector, function(){
    casper.click(delete_button_selector);
});
casper.waitForSelector(delete_input_selector, function(){
    casper.wait(100);
});


// again react.js magic, we should enter symbols one-by-one :(
function enter_symbol(rest){
    if( rest.length > 0){
        var symbol = rest.slice(0, 1);
        var new_rest = rest.slice(1);

        casper.then(function() {
            casper.sendKeys(delete_input_selector, symbol);
            enter_symbol(new_rest)
        });
    }
}
casper.then(function() {
    enter_symbol(repo_name);
});


casper.waitForSelector(delete_button_selector, function(){
//    casper.capture("200-before_confirm.png")
    casper.click(delete_button_selector);
});

//casper.then(function(){
////    casper.sendKeys(delete_input_selector, repo_name);
//    casper.sendKeys(delete_input_selector, "x");
//    casper.captureSelector("100-input_x.png", delete_input_selector);
//});
//
//casper.then(function(){
//    // casper.wait(1000);
//
//    casper.sendKeys(delete_input_selector, "zz");
//    casper.wait(2000);
//    casper.captureSelector("101-input_y.png", delete_input_selector);
//});


casper.waitForSelector(test_after_login_selector, function() {
    this.echo(this.getCurrentUrl());
//    this.capture("201-delete_done.png");
});



casper.run();

