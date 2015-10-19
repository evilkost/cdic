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
var fs = require('fs');
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
//    this.capture("000-login_page.png");
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
//    this.capture("001-login_should_be_done.png");
});


var choose_gh_repo_url = 'https://hub.docker.com/add/automated-build/github/orgs/?namespace=' + username;
var build_create_page_link_selector = "[href='/add/automated-build/github/form/" + GITHUB_USER + "/" + repo_name + "/']";


casper.thenOpen(choose_gh_repo_url, function(){
//    casper.echo("Target link: " + build_create_page_link_selector);
});



// WARNING: We couldn't simply open build creation page due to the react.js magic :(
casper.waitForSelector(build_create_page_link_selector, function() {

//    this.capture("100_before_select_gh_repo.png");
    this.click(build_create_page_link_selector);
});

var create_button_selector = x("(//form)[2]//button[text()='Create']");
var ta_selector = x("(//form)[2]//textarea");

casper.waitForSelector(create_button_selector);

casper.waitForSelector(ta_selector, function() {

//    this.capture("101_before_filling_form.png");
    this.sendKeys(ta_selector, "see README.md");

//    this.captureSelector("102_form_before_submit.png", x("(//form)[2]"));
//    this.captureSelector("103_ta_form_before_submit.png", ta_selector);
//    this.captureSelector("104_button_form_before_submit.png", create_button_selector);

//    this.capture("110_before_click_create.png");

    this.click(create_button_selector);
//    this.capture("111_at_click.png");
    this.wait(2000);
//    this.capture("200_end.png");

});



casper.run();

