define(function (require) {

  var module = require('ui/modules').get('kibana/efetch', ['kibana']);

  //This could be a security issue for some groups, so for testing only now
  module.config(function($sceDelegateProvider) {
      $sceDelegateProvider.resourceUrlWhitelist(['**']);
  });

  module.controller('EfetchVisController', function ($scope, $location, $element, Private) {
    $scope.getSrc = function(efetch_url, plugin, args) {
        return efetch_url + plugin + '?' + $location.absUrl().split('?')[1] + '&index=' + $scope.vis.indexPattern.title;
    };
  });
});
