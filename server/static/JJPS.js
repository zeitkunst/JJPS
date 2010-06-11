        $(window).load(function() {
                $('#slider').nivoSlider({
                    effect:'random', //Specify sets like: 'fold,fade,sliceDown'
                    slices:15,
                    animSpeed:500,
                    pauseTime:5000,
                    startSlide:0, //Set starting Slide (0 index)
                    directionNavHide:true, //Only show on hover
                    controlNav:false, //1,2,3...
                    controlNavThumbs:false, //Use thumbnails for Control Nav
                    keyboardNav:true, //Use left & right arrows
                    pauseOnHover:true, //Stop animation while hovering
                    captionOpacity:0.8, //Universal caption opacity
                    directionNav: false});
            });

