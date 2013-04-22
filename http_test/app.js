var express = require('express');

var app = express();

app.use(express.bodyParser());

allowedUserData = ['etoccalino'];


app.post('/:username', function (req, res) {
  user = req.params.username;

  if (allowedUserData.indexOf(user) == -1) {

    console.log('Data for user ' + user + ' is not allowed.');
    res.send(400, 'Bad Request');

  } else if (req.body.count === undefined) {

    console.log('Data for user ' + user + ' does not have a "count" value');
    res.send(400, 'Bad Request');

  }
  else {

  console.log(user + ': ' + req.body.count);
  res.send(202, 'Accepted');

  }
});

app.listen(3000);
console.log('Listening on port 3000');
