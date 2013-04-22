var express = require('express');

var app = express();

app.use(express.bodyParser());

allowedUserData = ['etoccalino'];


app.post('/:username', function (req, res) {
  user = req.params.username;

  if (user && (allowedUserData.indexOf(user) > -1) && (req.body.count !== undefined)) {
    console.log(user + ': ' + req.body.count);
    res.send(202, 'Accepted');
  }
  res.send(400, 'Bad Request')
});

app.listen(3000);
console.log('Listening on port 3000');
