var casper = require('casper').create({
//    verbose: true,
//    logLevel: "debug",
//    pageSettings: {
//        userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11"
//    },
    viewportSize: {
      width: 1920,
      height: 1080
    }
});
casper.options.waitTimeout = 10000; // milliseconds

// load helpers
var x = require("casper").selectXPath;
var fs = require('fs');
var utils = require('utils');

//debug

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
//


// load data
var repo_name = casper.cli.get("repo_name");
var credentials = casper.cli.get("credentials");
var save_to = casper.cli.get("save_to");

var data = JSON.parse(fs.read(credentials));

var username = data.username;
var password = data.password;
var github_username = data.github_username;

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

var choose_gh_repo_url = 'https://hub.docker.com/add/automated-build/github/orgs/?namespace=' + username;
var build_create_page_link_selector = "[href='/add/automated-build/github/form/" + github_username + "/" + repo_name + "/']";

casper.thenOpen(choose_gh_repo_url);

// WARNING: We couldn't simply open build creation page due to the react.js magic :(
casper.waitForSelector(build_create_page_link_selector, function() {
    this.click(build_create_page_link_selector);
});

var create_button_selector = x("(//form)[2]//button[text()='Create']");
//var create_button_selector = x("//button[text()='Create']");
var ta_selector = x("(//form)[2]//textarea");

var empty_description_selector = x("//p[text()='This field is required.']");


casper.waitForSelector(create_button_selector, function() {
    this.wait(1000);
    this.click(create_button_selector);
//    this.captureSelector("104_after_submit.png", create_button_selector);
});

casper.then(function() {
//    this.echo("Last step again");
    this.wait(1000);
    this.click(create_button_selector);
});

casper.waitForSelector(empty_description_selector, function() {

//    casper.echo("EMPTY DESCRIPTION");
    casper.wait(1000);
//    casper.captureSelector("202_form_before_submit.png", x("(//form)[2]"));
    casper.sendKeys(ta_selector, "see README.md");

});

casper.then(function(){
//    casper.wait(500);
//    casper.captureSelector("203_ta_form_before_submit.png", ta_selector);
    casper.click(create_button_selector);
//    casper.wait(1000);
//    casper.click(create_button_selector);
//    casper.capture("204_after_submit.png");

});
var test_project_was_created_selector = x("//a[text()='Repo Info']");
casper.waitForSelector(test_project_was_created_selector, function(){

    casper.echo("success!");

    var result = {
        "repo_name": repo_name,
        "status": "created"
    };

    casper.echo("saving to: " + save_to);
    fs.write(save_to, JSON.stringify(result), 'w');
});

casper.run();

