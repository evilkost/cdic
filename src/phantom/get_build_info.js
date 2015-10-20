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
casper.options.waitTimeout = 5000; // milliseconds

// load helpers
var x = require("casper").selectXPath;
var fs = require('fs');
var utils = require('utils');

// load data
var root_url = 'https://hub.docker.com';
var repo_name = casper.cli.get("repo_name");
var build_id = casper.cli.get("build_id");
var save_to = casper.cli.get("save_to");

var credentials = casper.cli.get("credentials");

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

var test_after_login_selector = x("//input[@placeholder='Type to filter repositories by name']");
casper.waitForSelector(test_after_login_selector);

//login done

var url  = 'https://hub.docker.com/r/' + username +'/' + repo_name + '/builds/' + build_id + '/';


casper.thenOpen(url);


td_selector = x("//table//td");

var info_table = {};


casper.then(function() {

    var table_nodes = this.getElementsInfo(td_selector);
    var i = 0;
    do {
        key = table_nodes[i].text;
        value = table_nodes[i+1].text;

        info_table[key] = value;
        i = i + 2;
    } while(i < table_nodes.length);

});

casper.then(function(){
////    utils.dump(info_list_tmp);
//
//    var i = 0;
//    do {
//        key = info_list_tmp[i];
//        value = info_list_tmp[i+1];
//
//        info_table[key] = value;
//        i = i + 2;
//    } while(i < info_list_tmp.length);
////    utils.dump(info_table);
});


var logs_selector = x("(//div//p)[2]");
casper.then(function(){

    var logs = casper.getElementInfo(logs_selector).text;

    var result = {
        "info_table": info_table,
        "logs": logs
    };

    utils.dump(result);
    casper.echo("saving to: " + save_to);
    fs.write(save_to, JSON.stringify(result), 'w');

});


casper.run();
