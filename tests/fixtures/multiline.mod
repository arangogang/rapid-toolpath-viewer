MODULE MultilineTest
  CONST robtarget pStart :=
    [[100.5, 200.3, 300.1],
     [0.707107, 0, 0.707107, 0],
     [0, 0, 0, 0],
     [9E+09, 9E+09, 9E+09, 9E+09, 9E+09, 9E+09]];
  CONST robtarget pEnd :=
    [[400, 500, 600],
     [1, 0, 0, 0],
     [0, 0, 0, 0],
     [9E+09, 9E+09, 9E+09, 9E+09, 9E+09, 9E+09]];

  PROC main()
    MoveL pStart, v100, fine, tool0;
    MoveL pEnd, v100, fine, tool0;
  ENDPROC
ENDMODULE
